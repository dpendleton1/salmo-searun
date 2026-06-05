import pandas as pd
from pathlib import Path

# Directory containing the annual pbn_matched_detections CSV files
data_dir = Path("data/NOAA Halifax Detection Data/PN/")

# Collect all matching files, excluding 2014 (empty file with a different schema)
files = [f for f in sorted(data_dir.glob("pbn_matched_detections*.csv"))]

# Read all files; depth columns are read as strings to handle mixed types
# across years (2010 and 2016 have non-numeric values in these columns)
dat_otn = pd.concat([
    pd.read_csv(f, dtype={"bottomDepth": str, "receiverDepth": str})
    for f in files
], ignore_index=True)

# Cast depth columns to float; invalid/empty strings become NaN
dat_otn["bottomDepth"] = pd.to_numeric(dat_otn["bottomDepth"], errors="coerce")
dat_otn["receiverDepth"] = pd.to_numeric(dat_otn["receiverDepth"], errors="coerce")

# Parse dateCollectedUTC explicitly in case parse_dates silently failed
dat_otn["dateCollectedUTC"] = pd.to_datetime(dat_otn["dateCollectedUTC"], format="ISO8601", utc=True)

# Strip timezone info before writing (values are already UTC)
dat_otn["dateCollectedUTC"] = dat_otn["dateCollectedUTC"].dt.tz_localize(None)

# Extract the digits after the last dash in tagName as an integer ID code
# e.g. A69-1601-8651 -> 8651
dat_otn["IDCode"] = dat_otn["tagName"].str.split("-").str[-1].astype("Int64")

# Drop columns not needed for this analysis
dat_otn.drop(columns=[
    "collectionCode", "dateLastModified", "geometry","sensorRaw",
    "sensorName", "sensorType", "sensorValue", "sensorUnit",
    "geodeticDatum", "uncorrectedDateCollectedUTC", "contactPOC", "contactPI",
    "citation","codeSpace","scientificName","commonName","detectedBy",
    'receiverDepth','bottomDepth', 'localArea'
], inplace=True)

# add Year column based on the year of the first detection time (FirstTS)
dat_otn['Year'] = dat_otn['dateCollectedUTC'].dt.year

# Rename columns
dat_otn.rename(columns={
    "decimalLongitude": "Longitude",
    "decimalLatitude": "Latitude",
    "dateCollectedUTC": "DetectDateTime",
    "station": "SiteCode",
}, inplace=True)

# add "OTN" identier for the source of the data
dat_otn['Source'] = 'OTN'

# Rearrange columns
dat_otn = dat_otn[
    ['Source', 'Year', 'IDCode', 'SiteCode', 'DetectDateTime', 'Latitude', 'Longitude', 
    'receiver','tagName', 'catalogNumber','unqDetecID']
]

dat_otn = dat_otn.sort_values(['Year', 'IDCode', 'DetectDateTime']).reset_index(drop=True)
dat_otn.head()

# Write the dat_otn dataset to a single CSV in the same directory
dat_otn.to_csv(data_dir / "dat_otn.csv", index=False)
