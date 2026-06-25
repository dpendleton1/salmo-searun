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

# this works
# cols_wanted = [
#     'SiteCode', 'ReceiverSN', 'PingerIDCode', 'DetectDateTime',
#     'RefUTMEast', 'RefUTMNorth', 'RiverKm',
#     'ForkLength', 'Weight', 'OriginCode', 'ArrayGroup', 'DeploymentType'
# ]

# try this combo. this worked
cols_wanted = [
    'SiteCode', 'ReceiverSN', 'PingerIDCode', 'PingerSN', 'DetectDateTime','DetectionID',
    'RefUTMEast', 'RefUTMNorth',
    'RiverKm','ForkLength', 'Weight', 
    'OriginCode', 'ArrayGroup', 'Array', 'LocationGroup',
    'DeploymentType', 'DeployDateTime','DepUTMEast','DepUTMNorth',
    'SmoltDetailsID','SpeciesCode'
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

# determine how many records to not have a numeric value for RiverKm
# Check percentage of non-numeric values in RiverKm
total = len(dat_nefsc)
numeric_river_km = pd.to_numeric(dat_nefsc['RiverKm'], errors='coerce')
non_numeric_count = numeric_river_km.isna().sum()
print(f"Total records: {total}")
print(f"Non-numeric records (including missing): {non_numeric_count}")
print(f"Percentage: {(non_numeric_count / total) * 100:.2f}%")

# list SiteCodes for records that do not have a numeric value for RiverKm
# Find rows where RiverKm cannot be converted to numeric
numeric_river_km = pd.to_numeric(dat_nefsc['RiverKm'], errors='coerce')
non_numeric_rows = dat_nefsc[numeric_river_km.isna()]
# Get unique SiteCodes
unique_non_numeric_sites = non_numeric_rows['SiteCode'].unique()
print(f"Unique SiteCodes with non-numeric RiverKm: {len(unique_non_numeric_sites)}")
print(sorted(unique_non_numeric_sites))
# >>> ['OR01', 'OR02', 'VHP1W', 'VHP2E', 'VHP2W', 'VHP3W', 'VIBL01', 'WEBBER01']
# based on that, we can eliminate records with RiverKm > 0 AND where RiverKm has no numeric value
#    because all those SiteCodes are not in the ocean

# Remove records with RiverKm > 0 (i.e., keep only records in the ocean) OR SiteCode == 'RELEASE'
is_release = dat_nefsc['SiteCode'] == 'RELEASE'
# Use fillna(1) to replace missing values of RiverKm with 1, 
# thus excluding them from this analysis, since 1 >= -3 
# identify rows where RiverKm is <= -3 (Fort Point is at -3.88)
is_river_minus3 = dat_nefsc['RiverKm'].fillna(1) <= -3
# Keep only rows where RiverKm <= 0 OR it is a RELEASE record
dat_nefsc = dat_nefsc[is_river_minus3 | is_release].reset_index(drop=True)

# Now we can proceed with processing the data

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
    ['Source', 'Year',
    'SiteCode', 'ReceiverSN', 'IDCode', 'PingerSN', 'DetectDateTime', 'DetectionID',
    'RefUTMEast', 'RefUTMNorth',
    'RiverKm', 'ForkLength', 'Weight',
    'OriginCode', 'ArrayGroup', 'Array', 'LocationGroup',
    'DeploymentType', 'DeployDateTime', 'DepUTMEast', 'DepUTMNorth',
    'SmoltDetailsID', 'SpeciesCode']
]

# save dat_nefsc to csv
dat_nefsc.to_csv(out_dir / "dat_nefsc.csv", index=False)

# Keep only SiteCodes in the ocean
prefixes_to_keep = ('FP', 'WP0', 'DH', 'LH', 'ER', 'MH', 'OH', 'GoMOOSF', 'GoMOOSE')

# 1. Identify first match time at kept sites
first_match = (
    dat_nefsc[dat_nefsc['SiteCode'].str.startswith(prefixes_to_keep, na=False)]
    .groupby('IDCode')['DetectDateTime']
    .min()
    .rename('FirstMatchTime')
)

# 2. Dataset A: Records at or after FirstMatchTime
after_first_match = dat_nefsc['DetectDateTime'] >= first_match.reindex(dat_nefsc['IDCode']).values
dataset_a = dat_nefsc[after_first_match].copy()

# 3. Dataset B: Only 'RELEASE' records
dataset_b = dat_nefsc[dat_nefsc['SiteCode'] == 'RELEASE'].copy()

# 4. Concatenate and sort
dat_nefsc_pb_forward = (
    pd.concat([dataset_a, dataset_b], ignore_index=True)
    .sort_values(['Year', 'IDCode', 'DetectDateTime'])
    .reset_index(drop=True)
)

dat_nefsc_pb_forward.to_csv(out_dir / "dat_nefsc_pb_forward.csv", index=False)



#----------------
# 1. First, find the first match time using only the keep-prefixes
first_match = (
    dat_nefsc[dat_nefsc['SiteCode'].str.startswith(prefixes_to_keep, na=False)]
    .groupby('IDCode')['DetectDateTime']
    .min()
    .rename('FirstMatchTime')
)

# 1. Dataset A: Records that are after the first match time at a kept site
# Note: This automatically excludes the pre-match detections (like BNHP01)
after_first_match = dat_nefsc['DetectDateTime'] >= first_match.reindex(dat_nefsc['IDCode']).values
dataset_a = dat_nefsc[after_first_match].copy()

# 2. Dataset B: Only 'RELEASE' records 
# (This captures all release records regardless of time)
dataset_b = dat_nefsc[dat_nefsc['SiteCode'] == 'RELEASE'].copy()

# 3. Combine and drop potential duplicates
# We drop duplicates in case a RELEASE record also happens to be after FirstMatchTime
dat_nefsc_pb_forward = (
    pd.concat([dataset_a, dataset_b], ignore_index=True)
    .drop_duplicates()
    .sort_values(['Year', 'IDCode', 'DetectDateTime'])
    .reset_index(drop=True)
)

dat_nefsc_pb_forward = dat_nefsc_pb_forward.sort_values(['Year', 'IDCode', 'DetectDateTime']).reset_index(drop=True)
dat_nefsc_pb_forward.to_csv(out_dir / "dat_nefsc_pb_forward.csv", index=False)

# Keep only rows where DeploymentType is 'Deploy'
dat_nefsc_pb_forward_deploy = dat_nefsc_pb_forward[dat_nefsc_pb_forward['DeploymentType'] == 'Deploy'].reset_index(drop=True)
dat_nefsc_pb_forward_deploy.to_csv(out_dir / "dat_nefsc_pb_forward_deploy.csv", index=False)

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

dat_nefsc_pb_forward_deploy[['Latitude', 'Longitude']] = dat_nefsc_pb_forward_deploy.apply(utm_to_latlon, axis=1)
#dat_nefsc_pb_forward_deploy[['Latitude', 'Longitude']].dropna().head() #drops any columns that are missing either latitude or longitude
dat_nefsc_pb_forward_deploy.to_csv(out_dir / "dat_nefsc_pb_forward_deploy_latlon.csv", index=False)
