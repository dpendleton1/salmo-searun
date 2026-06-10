from operator import index
import subprocess
import pandas as pd
from pathlib import Path
from io import StringIO
import re

db_dir = Path("data/Penobscot Access Databases")
out_dir = db_dir / "csv_export"
out_dir.mkdir(exist_ok=True)

accdb_files = sorted(db_dir.glob("*.accdb"))
tables = ['tblDetection', 'tblSmoltDetails', 'tblLocations', 'tblDeployment']

cols_wanted = [
    'SiteCode', 'ReceiverSN', 'PingerIDCode', 'DetectDateTime',
    'RefUTMEast', 'RefUTMNorth', 'RiverKm',
    'ForkLength', 'Weight'
]

all_years = []

for db_file in accdb_files:
    year = int(re.search(r'(\d{4})', db_file.name).group(1))
    is_edt = 'EDT' in db_file.name
    print(f"Processing {year} ({'EDT' if is_edt else 'UTC'})...")

    raw = {}
    for table in tables:
        result = subprocess.run(
            ['mdb-export', str(db_file), table],
            capture_output=True, text=True
        )
        raw[table] = pd.read_csv(StringIO(result.stdout), low_memory=False)

    det   = raw['tblDetection']
    smolt = raw['tblSmoltDetails']
    loc   = raw['tblLocations']
    dep   = raw['tblDeployment'].rename(columns={"RecieverSN": "ReceiverSN"})

    # Normalise RiverKM / RiverKm column name
    loc.columns = [c if c != 'RiverKM' else 'RiverKm' for c in loc.columns]

    # Convert DetectDateTime to UTC
    det['DetectDateTime'] = pd.to_datetime(det['DetectDateTime'])
    if is_edt:
        det['DetectDateTime'] = (
            det['DetectDateTime']
            .dt.tz_localize('America/New_York', ambiguous='NaT', nonexistent='NaT')
            .dt.tz_convert('UTC')
            .dt.tz_localize(None)   # strip tzinfo → naive UTC
        )

    # Merges
    dep_loc   = dep.merge(loc, on="SiteCode", how="left", suffixes=("_dep", "_loc"))
    det_smolt = det.merge(smolt, on="PingerIDCode", how="left", suffixes=("_det", "_smolt"))
    dat_nefsc  = det_smolt.merge(dep_loc, on="ReceiverSN", how="left", suffixes=("", "_dep"))

    # Keep only columns present in this year
    available = [c for c in cols_wanted if c in dat_nefsc.columns]
    dat_nefsc = dat_nefsc[available].copy()
    dat_nefsc['Year'] = year

    all_years.append(dat_nefsc)

# Combine all years
dat_nefsc = pd.concat(all_years, ignore_index=True)

# create latitude and longitude columns from easting, northing and UTMZone
# convert easting and northing to lat and long
# WARNING: this takes a long time because it uses pyproj's Transformer for each row, which is not vectorized (i think)
from pyproj import Proj, Transformer
def utm_to_latlon(row):
    if pd.isna(row['RefUTMEast']) or pd.isna(row['RefUTMNorth']):
        return pd.Series([None, None])
    transformer = Transformer.from_crs(
        "EPSG:32619",  # WGS84 UTM Zone 19N
        "EPSG:4326",
        always_xy=True
    )
    lon, lat = transformer.transform(row['RefUTMEast'], row['RefUTMNorth'])
    return pd.Series([lat, lon])

dat_nefsc[['Latitude', 'Longitude']] = dat_nefsc.apply(utm_to_latlon, axis=1)
# dat_nefsc[['Latitude', 'Longitude']].dropna().head() #drops any columns that are missing either latitude or longitude

# save dat_nefsc to csv
# save after calculating lat/lon from northing/easting because it takes a long time and we don't want to have to recalculate it every time we run the script
dat_nefsc.to_csv(out_dir / "dat_nefsc_latlon_4reload.csv", index=False)
# reload dat_nefsc from csv to avoid having to recalculate lat/lon every time we run the script
# dat_nefsc = pd.read_csv(out_dir / "dat_nefsc_latlon_4reload.csv")

# Rename some columns
dat_nefsc = dat_nefsc.rename(columns={'PingerIDCode': 'IDCode'})

# add "NEFSC" identier for the source of the data so it can be identified when we combine with OTN data
dat_nefsc['Source'] = 'NEFSC'

# add Year column based on the year of the first detection time (FirstTS)
dat_nefsc['Year'] = dat_nefsc['DetectDateTime'].dt.year

# remove Year < 2008
dat_nefsc = dat_nefsc[dat_nefsc['Year'] >= 2008].reset_index(drop=True)

# sort
dat_nefsc = dat_nefsc.sort_values(['Year', 'IDCode', 'DetectDateTime']).reset_index(drop=True)

# Rearrange columns
dat_nefsc = dat_nefsc[
    ['Source', 'Year', 'IDCode', 'SiteCode', 'DetectDateTime', 'Longitude', 'Latitude', 
    'RiverKm','ForkLength', 'Weight']
]

# save dat_nefsc to csv
dat_nefsc.to_csv(out_dir / "dat_nefsc.csv", index=False)

# Keep only SiteCodes in the ocean
prefixes_to_keep = ('FP', 'WP0', 'DH', 'LH', 'ER', 'MH', 'OH', 'GoMOOSF', 'GoMOOSE')
dat_nefsc_pb = dat_nefsc[dat_nefsc['SiteCode'].str.startswith(prefixes_to_keep, na=False)]

# Find the first matching detection time per fish
first_match = (
    dat_nefsc_pb[dat_nefsc_pb['SiteCode'].str.startswith(prefixes_to_keep, na=False)]
    .groupby('IDCode')['DetectDateTime']
    .min()
    .rename('FirstMatchTime')
)

# Keep all records at or after that first match time
dat_nefsc_pb_forward = (
    dat_nefsc_pb
    .assign(IDCode=pd.to_numeric(dat_nefsc['IDCode'], errors='coerce'))
    .join(first_match, on='IDCode')
    .query('DetectDateTime >= FirstMatchTime')
    .drop(columns='FirstMatchTime')
    .sort_values(['Year', 'IDCode', 'DetectDateTime'])
    .reset_index(drop=True)
)

dat_nefsc_pb_forward.to_csv(out_dir / "dat_nefsc_pb_forward.csv", index=False)

# BELOW THIS LINE WE DON'T NEED. KEEPING INCASE I WANT THIS CODE LATER
# summary_fl = (
#     first_last
#     .rename(columns={'first': 'FirstTS', 'last': 'LastTS'})
#     .merge(
#         summary.drop(columns='DetectDateTime').drop_duplicates(subset=['IDCode', 'SiteCode']),
#         on=['IDCode', 'SiteCode']
#     )
#     .sort_values(['IDCode', 'FirstTS'])
#     .reset_index(drop=True)
# )

# summary_fl.shape

# # reorder columns to have Year first, then PingerIDCode, SiteCode, FirstTS, LastTS, and then the rest of the columns
# cols = summary_fl.columns.tolist()
# cols = ['Year', 'IDCode', 'SiteCode', 'FirstTS', 'LastTS'] + [c for c in cols if c not in ['Year', 'IDCode', 'SiteCode', 'FirstTS', 'LastTS']]
# summary_fl = summary_fl[cols]

# # sort the dataframe by Year, then PingerIDCode, then SiteCode, then FirstTS
# summary_fl = summary_fl.sort_values(['Year', 'IDCode', 'FirstTS', 'SiteCode']).reset_index(drop=True)

# summary_fl.head()
# summary_fl.shape
# summary_fl.to_csv(out_dir / "combined_all_years_ocean_onlyFL.csv", index=False)