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
    'ForkLength', 'TotalLength', 'Weight'
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

# Keep only SiteCodes in the ocean
prefixes_to_keep = ('FP', 'WP0', 'DH', 'LH', 'ER', 'MH', 'OH', 'GoMOOSF', 'GoMOOSE')
all_combined = all_combined[all_combined['SiteCode'].str.startswith(prefixes_to_keep, na=False)]

# Keep all detections, sorted by PingerIDCode and DetectDateTime
# summary = (
#     all_combined
#     .sort_values(["PingerIDCode", "DetectDateTime"])
#     .reset_index(drop=True)
# )

summary = (
    all_combined
    .assign(PingerIDCode=pd.to_numeric(all_combined['PingerIDCode'], errors='coerce'))
    .sort_values(["PingerIDCode", "DetectDateTime"])
    .reset_index(drop=True)
)

summary.to_csv(out_dir / "combined_all_years_ocean_only.csv", index=False)
summary.shape
