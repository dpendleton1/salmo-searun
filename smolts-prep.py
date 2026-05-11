import pandas as pd

df_allsmolts = pd.read_csv('data/allsmolts.csv', low_memory=False)


for col in ['Period', 'FirstTS', 'LastTS']:
    df_allsmolts[col] = pd.to_datetime(df_allsmolts[col], format='mixed').dt.strftime('%Y-%m-%d %H:%M:%S')

df_allsmolts[['Period', 'FirstTS', 'LastTS']].head()

# clean up inconsistencies

# 1. Drop fully empty columns
df_allsmolts.drop(columns=['Frequency', 'avgPower', 'AntennaID'], inplace=True)

# 2. TagId: coerce to numeric (Int64 to support NaN)
df_allsmolts['TagId'] = pd.to_numeric(df_allsmolts['TagId'], errors='coerce').astype('Int64')

# 3. SensorType: replace blank/whitespace strings with NaN
df_allsmolts['SensorType'] = df_allsmolts['SensorType'].str.strip().replace('', pd.NA)

# 4. RxID: coerce to numeric (Int64 to support NaN)
df_allsmolts['RxID'] = pd.to_numeric(df_allsmolts['RxID'], errors='coerce').astype('Int64')

# 5. UTMZone: cast float to Int64
df_allsmolts['UTMZone'] = df_allsmolts['UTMZone'].astype('Int64')

# Verify
for col in df_allsmolts.columns:
    dtype = df_allsmolts[col].dtype
    n_unique = df_allsmolts[col].nunique()
    sample = df_allsmolts[col].dropna().head(3).tolist()
    print(f"{col:20s} | {str(dtype):10s} | unique={n_unique:6} | sample={sample}")

# sort by TagID and FirstTS
df_allsmolts = df_allsmolts.sort_values(['TagId', 'FirstTS']).reset_index(drop=True)

# remove dates before 2008
df_allsmolts = df_allsmolts[df_allsmolts['Period'] > '2007-12-31 23:59:59'].reset_index(drop=True)
df_allsmolts.shape

# create a new column the concatenates Codespace and IDCode. These two columns are supposed to be concatenated in the TagId column, but that's not always the case.
df_allsmolts['TagCode'] = df_allsmolts['Codespace'] + '-' + df_allsmolts['IDCode'].astype(str)

# tagtype and Species only contain one value 'Acoustic' and 'ATS' so we can remove those columns
df_allsmolts = df_allsmolts.drop(columns=['tagtype', 'Species'])

# strip off numbers at the end of SiteCode entries to try and determine how many Sites there are. We think the number suffix represents receiver number.
import re
df_allsmolts['SiteCode_base'] = df_allsmolts['SiteCode'].map(lambda x: re.sub(r'\d+$', '', x) if pd.notna(x) else x)
df_allsmolts['SiteCode_base'].nunique()
sorted(df_allsmolts['SiteCode_base'].dropna().unique().tolist())

# convert easting and northing to lat and long
from pyproj import Proj, Transformer
def utm_to_latlon(row):
    if pd.isna(row['Easting']) or pd.isna(row['Northing']) or pd.isna(row['UTMZone']):
        return pd.Series([None, None])
    zone = int(row['UTMZone'])
    transformer = Transformer.from_crs(
        f"EPSG:{32600 + zone}",  # WGS84 UTM North
        "EPSG:4326",
        always_xy=True
    )
    lon, lat = transformer.transform(row['Easting'], row['Northing'])
    return pd.Series([lat, lon])

df_allsmolts[['Latitude', 'Longitude']] = df_allsmolts.apply(utm_to_latlon, axis=1)
df_allsmolts[['Latitude', 'Longitude']].dropna().head()


# write out a cleaned up .csv
df_allsmolts.to_csv('data/all_smolts_clean.csv', index=False)


# generate an interactive plot with all locations in this dataset

import plotly.express as px

df_plot = df_allsmolts[['Latitude', 'Longitude', 'LocationCode', 'SiteCode']].dropna(subset=['Latitude', 'Longitude']).drop_duplicates()

fig = px.scatter_map(
    df_plot,
    lat='Latitude',
    lon='Longitude',
    hover_data={'LocationCode': True, 'SiteCode': True, 'Latitude': ':.4f', 'Longitude': ':.4f'},
    zoom=5,
    height=700,
    title='Acoustic Receiver Locations'
)

fig.update_layout(map_style='open-street-map')
fig.show()
