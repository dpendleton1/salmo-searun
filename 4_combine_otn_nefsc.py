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

# Export combined dataset
merged.to_csv(out_dir / "dat_otn_nefsc_combined.csv", index=False)

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
