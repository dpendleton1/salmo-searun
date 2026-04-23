# Read TIDBITS data and convert UTM coordinates to lat/lon

import pandas as pd
import numpy as np
from pyproj import Transformer

# Read the CSV file
df = pd.read_csv('tidbits1325.csv')

# convert UTM coordinates to lat/lon
# Create transformer from UTM Zone 19N to WGS84 (lat/lon)
transformer = Transformer.from_crs("EPSG:32619", "EPSG:4326", always_xy=True)

# Convert coordinates (handle NaN values)
mask = df['Easting'].notna() & df['Northing'].notna()
lons = np.full(len(df), np.nan)
lats = np.full(len(df), np.nan)

lons[mask], lats[mask] = transformer.transform(
    df.loc[mask, 'Easting'].values, 
    df.loc[mask, 'Northing'].values
)

# Add new columns
df['Longitude'] = lons
df['Latitude'] = lats

# Save the updated file
#df.to_csv('data/Smolts 2013-25.csv', index=False)

print("Conversion complete!")
print(f"\nSample of converted coordinates:")
print(df[['Easting', 'Northing', 'Longitude', 'Latitude']].head(10))
print(f"\nLatitude range: {df['Latitude'].min():.6f} to {df['Latitude'].max():.6f}")
print(f"Longitude range: {df['Longitude'].min():.6f} to {df['Longitude'].max():.6f}")
print(f"\nTotal rows processed: {len(df)}")
print(f"Rows with coordinates: {mask.sum()}")

df.head()

