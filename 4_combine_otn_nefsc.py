"""
Combine OTN and NEFSC Datasets

This script loads the processed OTN and NEFSC deployment and detection datasets,
combines them into a unified tracking dataframe, identifies overlapping records
across sources, and exports the combined dataset.
"""

from pathlib import Path

import pandas as pd

# -----------------------------------------------------------------------------
# Configuration and Data Ingestion
# -----------------------------------------------------------------------------

out_dir = Path("data/output_files")

dat_nefsc_pb_forward_deploy_latlon = pd.read_csv(
    out_dir / "dat_nefsc_pb_forward_deploy_latlon.csv",
    parse_dates=["DetectDateTime"],
)
dat_otn = pd.read_csv(
    out_dir / "dat_otn.csv", parse_dates=["DetectDateTime"]
)

# -----------------------------------------------------------------------------
# Dataset Combination and Sorting
# -----------------------------------------------------------------------------

merged = pd.concat(
    [dat_otn, dat_nefsc_pb_forward_deploy_latlon], ignore_index=True, sort=False
)
merged["DetectDateTime"] = pd.to_datetime(
    merged["DetectDateTime"], format="ISO8601"
)
merged = merged.sort_values(["Year", "IDCode", "DetectDateTime"]).reset_index(
    drop=True
)

# Audit duplicate records matching on SiteCode and DetectDateTime across sources
dupes = (
    merged[merged["Source"].isin(["OTN", "NEFSC"])]
    .groupby(["SiteCode", "DetectDateTime"])
    .filter(lambda x: x["Source"].nunique() > 1)
)
print(f"Rows with matching SiteCode+DetectDateTime but different Source: {len(dupes)}")

# -----------------------------------------------------------------------------
# Spatial Filtering (Remove sites south of Portsmouth, NH / west of Chatham, MA / east of -50.0°)
# -----------------------------------------------------------------------------

# save a copy of 'merged' that includes erroneous locations
merged_with_bad_locs = merged

portsmouth_lat = 43.0718
chatham_lon = -69.9697
east_lon_threshold = -50.0

# Identify and remove records located south of Portsmouth (< 43.0718) and west of Chatham (< -69.9697)
is_south_west = (merged["Latitude"] < portsmouth_lat) & (merged["Longitude"] < chatham_lon)
print(f"Removing {is_south_west.sum()} records south of Portsmouth and west of Chatham.")

# Identify and remove records located east of -50.0 degrees (> -50.0)
is_east = merged["Longitude"] > east_lon_threshold
print(f"Removing {is_east.sum()} records east of -50.0 degrees longitude.")

# Save removed records to CSV
removed_records = merged[is_south_west | is_east]
removed_records.to_csv(out_dir / "dat_otn_nefsc_removed.csv", index=False)

merged = merged[~(is_south_west | is_east)].reset_index(drop=True)

# -----------------------------------------------------------------------------
# Deduplication of Release Records
# -----------------------------------------------------------------------------

# For release events with matching IDCode, DetectDateTime, and approximately equal
# Latitude/Longitude (rounded to 3 significant digits), prioritize Source == 'NEFSC'.
merged = (
    merged.assign(
        _is_nefsc=lambda df: df["Source"].apply(lambda s: 0 if s == "NEFSC" else 1),
        _lat_round=lambda df: df["Latitude"].round(3),
        _lon_round=lambda df: df["Longitude"].round(3),
    )
    .sort_values(["IDCode", "DetectDateTime", "_lat_round", "_lon_round", "_is_nefsc"])
    .drop_duplicates(
        subset=["IDCode", "DetectDateTime", "_lat_round", "_lon_round"],
        keep="first",
    )
    .drop(columns=["_is_nefsc", "_lat_round", "_lon_round"])
    .reset_index(drop=True)
)

merged.to_csv(out_dir / "dat_otn_nefsc_combined.csv", index=False)
