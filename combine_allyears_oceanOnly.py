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
    combined  = det_smolt.merge(dep_loc, on="ReceiverSN", how="left", suffixes=("", "_dep"))

    # Keep only columns present in this year
    available = [c for c in cols_wanted if c in combined.columns]
    combined = combined[available].copy()
    combined['Year'] = year

    all_years.append(combined)

# Combine all years
all_combined = pd.concat(all_years, ignore_index=True)

# Rename some columns
all_combined = all_combined.rename(columns={'PingerIDCode': 'IDCode'})
all_combined = all_combined.rename(columns={'RefUTMEast': 'Easting'})
all_combined = all_combined.rename(columns={'RefUTMNorth': 'Northing'})

# add Year column based on the year of the first detection time (FirstTS)
all_combined['Year'] = all_combined['DetectDateTime'].dt.year

# remove Year < 2012
all_combined = all_combined[all_combined['Year'] >= 2012].reset_index(drop=True)

# save all_combined to csv
all_combined.to_csv(out_dir / "all_combined.csv", index=False)

# Keep only SiteCodes in the ocean
prefixes_to_keep = ('FP', 'WP0', 'DH', 'LH', 'ER', 'MH', 'OH', 'GoMOOSF', 'GoMOOSE')
all_combined = all_combined[all_combined['SiteCode'].str.startswith(prefixes_to_keep, na=False)]

# Find the first matching detection time per fish
first_match = (
    all_combined[all_combined['SiteCode'].str.startswith(prefixes_to_keep, na=False)]
    .groupby('IDCode')['DetectDateTime']
    .min()
    .rename('FirstMatchTime')
)

# Keep all records at or after that first match time
summary = (
    all_combined
    .assign(IDCode=pd.to_numeric(all_combined['IDCode'], errors='coerce'))
    .join(first_match, on='IDCode')
    .query('DetectDateTime >= FirstMatchTime')
    .drop(columns='FirstMatchTime')
    .sort_values(['IDCode', 'DetectDateTime'])
    .reset_index(drop=True)
)

grp = summary.groupby(['IDCode', 'SiteCode'])['DetectDateTime']

first_last = pd.concat([grp.min(), grp.max()], axis=1)
first_last.columns = ['first', 'last']
first_last = first_last.reset_index()

summary_fl = (
    summary
    .merge(first_last, on=['IDCode', 'SiteCode'])
    .query('DetectDateTime == first or DetectDateTime == last')
    .drop(columns=['first', 'last'])
    .drop_duplicates()
    .sort_values(['IDCode', 'DetectDateTime'])
    .reset_index(drop=True)
)

# # Keep all detections, sorted by PingerIDCode and DetectDateTime
# summary = (
#     all_combined
#     .assign(PingerIDCode=pd.to_numeric(all_combined['PingerIDCode'], errors='coerce'))
#     .sort_values(["PingerIDCode", "DetectDateTime"])
#     .reset_index(drop=True)
# )

# Instead of having one row for the first detection and one row for the last detection, 
# make one row for each PingerIDCode and separate columns for first detection ('FirstTS') 
# and a column for second detection ('LastTS'). Remove the 'DetectDateTime' column.

summary_fl = (
    first_last
    .rename(columns={'first': 'FirstTS', 'last': 'LastTS'})
    .merge(
        summary.drop(columns='DetectDateTime').drop_duplicates(subset=['IDCode', 'SiteCode']),
        on=['IDCode', 'SiteCode']
    )
    .sort_values(['IDCode', 'FirstTS'])
    .reset_index(drop=True)
)

summary_fl.shape


# reorder columns to have Year first, then PingerIDCode, SiteCode, FirstTS, LastTS, and then the rest of the columns
cols = summary_fl.columns.tolist()
cols = ['Year', 'IDCode', 'SiteCode', 'FirstTS', 'LastTS'] + [c for c in cols if c not in ['Year', 'IDCode', 'SiteCode', 'FirstTS', 'LastTS']]
summary_fl = summary_fl[cols]

# sort the dataframe by Year, then PingerIDCode, then SiteCode, then FirstTS
summary_fl = summary_fl.sort_values(['Year', 'IDCode', 'FirstTS', 'SiteCode']).reset_index(drop=True)

summary_fl.head()
summary_fl.shape
summary_fl.to_csv(out_dir / "combined_all_years_ocean_onlyFL.csv", index=False)
