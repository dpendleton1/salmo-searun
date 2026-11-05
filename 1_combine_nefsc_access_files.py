"""
Combine and Process NEFSC Access Database Files

This script reads raw Microsoft Access databases (.accdb) exported via mdb-tools,
standardizes datetimes and column names, applies spatial filtering (Penobscot
Bay and coastal/ocean receiver arrays), calculates forward-moving tracks from
first oceanic detection, and transforms UTM coordinates to latitude/longitude.
"""

from io import StringIO
from pathlib import Path
import re
import subprocess

import pandas as pd
from pyproj import Transformer

# -----------------------------------------------------------------------------
# Configuration and Setup
# -----------------------------------------------------------------------------

db_dir = Path("data/Penobscot Access Databases")
out_dir = Path("data/output_files")
out_dir.mkdir(exist_ok=True)

accdb_files = sorted(db_dir.glob("*.accdb"))
tables = ["tblDetection", "tblSmoltDetails", "tblLocations", "tblDeployment"]

cols_wanted = [
    "SiteCode",
    "ReceiverSN",
    "PingerIDCode",
    "PingerSN",
    "DetectDateTime",
    "DetectionID",
    "RefUTMEast",
    "RefUTMNorth",
    "RiverKm",
    "ForkLength",
    "Weight",
    "OriginCode",
    "ArrayGroup",
    "Array",
    "LocationGroup",
    "DeploymentType",
    "DeployDateTime",
    "DepUTMEast",
    "DepUTMNorth",
    "SmoltDetailsID",
    "SpeciesCode",
]

# -----------------------------------------------------------------------------
# 1. Ingest and Combine Annual Access Database Exports
# -----------------------------------------------------------------------------

all_years = []

for db_file in accdb_files:
    year = int(re.search(r"(\d{4})", db_file.name).group(1))
    is_edt = "EDT" in db_file.name
    print(f"Processing {year} ({'EDT' if is_edt else 'UTC'})...")

    raw = {}
    for table in tables:
        result = subprocess.run(
            ["mdb-export", str(db_file), table], capture_output=True, text=True
        )
        raw[table] = pd.read_csv(StringIO(result.stdout), low_memory=False)

    det = raw["tblDetection"]
    smolt = raw["tblSmoltDetails"]
    loc = raw["tblLocations"]
    dep = raw["tblDeployment"].rename(columns={"RecieverSN": "ReceiverSN"})

    # Normalize RiverKM to RiverKm
    loc.columns = [c if c != "RiverKM" else "RiverKm" for c in loc.columns]

    # Convert detection timestamps to UTC
    det["DetectDateTime"] = pd.to_datetime(det["DetectDateTime"])
    if is_edt:
        det["DetectDateTime"] = (
            det["DetectDateTime"]
            .dt.tz_localize(
                "America/New_York", ambiguous="NaT", nonexistent="NaT"
            )
            .dt.tz_convert("UTC")
            .dt.tz_localize(None)
        )

    # Merge detection, deployment, location, and tag details
    dep_loc = dep.merge(loc, on="SiteCode", how="left", suffixes=("_dep", "_loc"))
    det_smolt = det.merge(
        smolt, on="PingerIDCode", how="left", suffixes=("_det", "_smolt")
    )
    dat_nefsc = det_smolt.merge(
        dep_loc, on="ReceiverSN", how="left", suffixes=("", "_dep")
    )

    # Retain only desired columns present in this year's export
    available = [c for c in cols_wanted if c in dat_nefsc.columns]
    dat_nefsc = dat_nefsc[available].copy()
    dat_nefsc["Year"] = year

    all_years.append(dat_nefsc)

dat_nefsc = pd.concat(all_years, ignore_index=True)

# -----------------------------------------------------------------------------
# 2. Spatial Filtering (Ocean / Coastal Arrays)
# -----------------------------------------------------------------------------

# Filter out riverine/estuarine records with RiverKm > -3 (except RELEASE records)
total = len(dat_nefsc)
numeric_river_km = pd.to_numeric(dat_nefsc["RiverKm"], errors="coerce")
non_numeric_count = numeric_river_km.isna().sum()

print(f"Total records: {total}")
print(f"Non-numeric RiverKm records: {non_numeric_count}")
print(f"Percentage: {(non_numeric_count / total) * 100:.2f}%")

is_release = dat_nefsc["SiteCode"] == "RELEASE"
is_river_minus3 = dat_nefsc["RiverKm"].fillna(1) <= -3
dat_nefsc = dat_nefsc[is_river_minus3 | is_release].reset_index(drop=True)

# -----------------------------------------------------------------------------
# 3. Data Standardization and Column Cleanup
# -----------------------------------------------------------------------------

#PingerIDCode and IDCode are the same, but labeled differently across years. Need to standardize terms.
dat_nefsc = dat_nefsc.rename(columns={"PingerIDCode": "IDCode"})
#Idenitfy the source, i.e. "NEFSC", "USGS", "OTN"
dat_nefsc["Source"] = "NEFSC"
#This is duplicative as Year is added in above. However in this case, Year is taken from the actual datetime
dat_nefsc["Year"] = dat_nefsc["DetectDateTime"].dt.year 

# Restrict to 2008 and later. No need for earlier data, as that is from USGS and that dataset has problems. Additionally, it may not be part of this workflow. OTN data is brought in later.
dat_nefsc = dat_nefsc[dat_nefsc["Year"] >= 2008].reset_index(drop=True)
# Sort everything so it looks nice
dat_nefsc = dat_nefsc.sort_values(
    ["Year", "IDCode", "DetectDateTime"]
).reset_index(drop=True)

# Reorder columns
dat_nefsc = dat_nefsc[
    [
        "Source",
        "Year",
        "SiteCode",
        "ReceiverSN",
        "IDCode",
        "PingerSN",
        "DetectDateTime",
        "DetectionID",
        "RefUTMEast",
        "RefUTMNorth",
        "RiverKm",
        "ForkLength",
        "Weight",
        "OriginCode",
        "ArrayGroup",
        "Array",
        "LocationGroup",
        "DeploymentType",
        "DeployDateTime",
        "DepUTMEast",
        "DepUTMNorth",
        "SmoltDetailsID",
        "SpeciesCode",
    ]
]

dat_nefsc.to_csv(out_dir / "dat_nefsc.csv", index=False)

# -----------------------------------------------------------------------------
# 4. Penobscot Bay Forward-Migration Subsetting. Goal is to remove detections upstream of Penobscot Bay receivers.
# -----------------------------------------------------------------------------

prefixes_to_keep = (
    "FP",
    "WP0",
    "DH",
    "LH",
    "ER",
    "MH",
    "OH",
    "GoMOOSF",
    "GoMOOSE",
)

# Identify first detection timestamp at coastal/ocean arrays
first_match = (
    dat_nefsc[dat_nefsc["SiteCode"].str.startswith(prefixes_to_keep, na=False)]
    .groupby("IDCode")["DetectDateTime"]
    .min()
    .rename("FirstMatchTime")
)

# Dataset A: Detections at or after first oceanic array match
after_first_match = (
    dat_nefsc["DetectDateTime"] >= first_match.reindex(dat_nefsc["IDCode"]).values
)
dataset_a = dat_nefsc[after_first_match].copy()

# Dataset B: Release records
dataset_b = dat_nefsc[dat_nefsc["SiteCode"] == "RELEASE"].copy()

# Combine, sort, and export forward-migration dataset
dat_nefsc_pb_forward = (
    pd.concat([dataset_a, dataset_b], ignore_index=True)
    .sort_values(["Year", "IDCode", "DetectDateTime"])
    .reset_index(drop=True)
)
dat_nefsc_pb_forward.to_csv(out_dir / "dat_nefsc_pb_forward.csv", index=False)

# Filter for active deployments only
dat_nefsc_pb_forward_deploy = dat_nefsc_pb_forward[
    dat_nefsc_pb_forward["DeploymentType"] == "Deploy"
].reset_index(drop=True)
dat_nefsc_pb_forward_deploy.to_csv(
    out_dir / "dat_nefsc_pb_forward_deploy.csv", index=False
)

# -----------------------------------------------------------------------------
# 5. UTM to Latitude / Longitude Coordinate Transformation
# -----------------------------------------------------------------------------


def utm_to_latlon(row):
    """Convert UTM Zone 19N (EPSG:32619) coordinates to WGS84 Lat/Lon (EPSG:4326)."""
    if pd.isna(row["RefUTMEast"]) or pd.isna(row["RefUTMNorth"]):
        return pd.Series([None, None])
    transformer = Transformer.from_crs(
        "EPSG:32619", "EPSG:4326", always_xy=True
    )
    lon, lat = transformer.transform(row["RefUTMEast"], row["RefUTMNorth"])
    return pd.Series([lat, lon])


dat_nefsc_pb_forward_deploy[["Latitude", "Longitude"]] = (
    dat_nefsc_pb_forward_deploy.apply(utm_to_latlon, axis=1)
)
dat_nefsc_pb_forward_deploy.to_csv(
    out_dir / "dat_nefsc_pb_forward_deploy_latlon.csv", index=False
)
