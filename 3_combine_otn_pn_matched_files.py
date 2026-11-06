"""
Combine and Process OTN 'pbn_matched' Detection Files

This script reads annual OTN pbn_matched_yyyy.csv files, consolidates
them, identifies and exports cross-file duplicates, standardizes timestamps and
column names, extracts tag ID codes, and writes out the cleaned dataset.
"""

from pathlib import Path

import pandas as pd

# -----------------------------------------------------------------------------
# Configuration and Data Ingestion
# -----------------------------------------------------------------------------

out_dir = Path("data/output_files")
out_dir.mkdir(exist_ok=True)

data_dir = Path("data/NOAA Halifax Detection Data/PN/")
files = sorted(data_dir.glob("pbn_matched_detections*.csv"))

# Read all files, retaining source file tracking for duplicate auditing
data_frames = []
for f in files:
    temp_df = pd.read_csv(f, dtype={"bottomDepth": str, "receiverDepth": str})
    temp_df["SourceFile"] = f.name
    data_frames.append(temp_df)

dat_otn = pd.concat(data_frames, ignore_index=True)

# -----------------------------------------------------------------------------
# Duplicate Detection and Removal
# -----------------------------------------------------------------------------

# Identify rows duplicated across different source files (same records contained within separate YEAR folders!)
subset_cols = [c for c in dat_otn.columns if c != "SourceFile"]
duplicates = dat_otn[dat_otn.duplicated(subset=subset_cols, keep=False)]
duplicates.to_csv(out_dir / "dat_otn_duplicates.csv", index=False)

# Remove exact duplicates and drop tracking column
dat_otn = dat_otn.drop_duplicates().drop(columns=["SourceFile"])

# -----------------------------------------------------------------------------
# Standardization and Column Cleanup
# -----------------------------------------------------------------------------

# Cast depth columns to float (invalid/empty strings become NaN)
dat_otn["bottomDepth"] = pd.to_numeric(dat_otn["bottomDepth"], errors="coerce")
dat_otn["receiverDepth"] = pd.to_numeric(
    dat_otn["receiverDepth"], errors="coerce"
)

# Parse and normalize timestamps to naive UTC
dat_otn["dateCollectedUTC"] = pd.to_datetime(
    dat_otn["dateCollectedUTC"], format="ISO8601", utc=True
)
dat_otn["dateCollectedUTC"] = dat_otn["dateCollectedUTC"].dt.tz_localize(None)

# Extract integer IDCode from tagName (e.g., A69-1601-8651 -> 8651)
dat_otn["IDCode"] = dat_otn["tagName"].str.split("-").str[-1].astype("Int64")
dat_otn["Year"] = dat_otn["dateCollectedUTC"].dt.year
dat_otn["Source"] = "OTN"

# Rename key columns for consistency with NEFSC Access files that were processed in script 1_combine_nefsc_access_files.py
dat_otn = dat_otn.rename(
    columns={
        "decimalLongitude": "Longitude",
        "decimalLatitude": "Latitude",
        "dateCollectedUTC": "DetectDateTime",
        "station": "SiteCode",
    }
)

# Reorder columns
dat_otn = dat_otn[
    [
        "Source",
        "Year",
        "IDCode",
        "SiteCode",
        "DetectDateTime",
        "Latitude",
        "Longitude",
        "receiver",
        "tagName",
        "catalogNumber",
        "unqDetecID",
        "organismID",
        "codeSpace",
        "scientificName",
        "collectionCode",
        "dateLastModified",
    ]
]

# Sort and export cleaned OTN dataset
dat_otn = dat_otn.sort_values(
    ["Year", "IDCode", "DetectDateTime"]
).reset_index(drop=True)
dat_otn.to_csv(out_dir / "dat_otn.csv", index=False)
