import pandas as pd

df_allsmolts = pd.read_csv('data/allsmolts.csv', low_memory=False)

## make data types within columns consistent. They are not consistent because I pasted two datasets together.

# datetimes
for col in ['Period', 'FirstTS', 'LastTS']:
    df_allsmolts[col] = pd.to_datetime(df_allsmolts[col], format='mixed').dt.strftime('%Y-%m-%d %H:%M:%S')

# TagId: coerce to numeric (Int64 to support NaN)
df_allsmolts['TagId'] = pd.to_numeric(df_allsmolts['TagId'], errors='coerce').astype('Int64')

# SensorType: replace blank/whitespace strings with NaN
df_allsmolts['SensorType'] = df_allsmolts['SensorType'].str.strip().replace('', pd.NA)

# RxID: coerce to numeric (Int64 to support NaN)
df_allsmolts['RxID'] = pd.to_numeric(df_allsmolts['RxID'], errors='coerce').astype('Int64')

# UTMZone: cast float to Int64
df_allsmolts['UTMZone'] = df_allsmolts['UTMZone'].astype('Int64')

# Drop fully empty columns
df_allsmolts.drop(columns=['Frequency', 'avgPower', 'AntennaID'], inplace=True)

# Verify
for col in df_allsmolts.columns:
    dtype = df_allsmolts[col].dtype
    n_unique = df_allsmolts[col].nunique()
    sample = df_allsmolts[col].dropna().head(3).tolist()
    print(f"{col:20s} | {str(dtype):10s} | unique={n_unique:6} | sample={sample}")

# sort by TagID and FirstTS
df_allsmolts = df_allsmolts.sort_values(['TagId', 'FirstTS']).reset_index(drop=True)

#####################################################################################################

# remove dates before 2008
df_allsmolts = df_allsmolts[df_allsmolts['Period'] > '2011-12-31 23:59:59'].reset_index(drop=True)
df_allsmolts.shape

# create a new column the concatenates Codespace and IDCode. These two columns are supposed to be concatenated in the TagId column, but that's not always the case.
df_allsmolts['TagCode'] = df_allsmolts['Codespace'] + '-' + df_allsmolts['IDCode'].astype(str)

# tagtype and Species only contain one value 'Acoustic' and 'ATS' so we can remove those columns
df_allsmolts = df_allsmolts.drop(columns=['tagtype', 'Species'])

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

# # write out a cleaned up .csv
# df_allsmolts.to_csv('data/all_smolts_clean.csv', index=False)

# # generate an interactive plot with all locations in this dataset
# import plotly.express as px

# df_plot = df_allsmolts[['Latitude', 'Longitude', 'LocationCode', 'SiteCode']].dropna(subset=['Latitude', 'Longitude']).drop_duplicates()

# fig = px.scatter_map(
#     df_plot,
#     lat='Latitude',
#     lon='Longitude',
#     hover_data={'LocationCode': True, 'SiteCode': True, 'Latitude': ':.4f', 'Longitude': ':.4f'},
#     zoom=5,
#     height=700,
#     title='Acoustic Receiver Locations'
# )

# fig.update_layout(map_style='open-street-map')
# fig.show()

# Prompt: 
# Identify FishID that were detected at 
# the following 'LocationCode' or 'SiteCode': FTPNT, FP02, FP03, 
# WP01, WP02, WP03, WP04, WP05
# Remove records that occurred earlier in time than the first 
# detection at one of the 'LocationCode' or 'SiteCode' listed above.

target_locations = {'FTPNT', 'FP02', 'FP03', 'WP01', 'WP02', 'WP03', 'WP04', 'WP05'}

at_target = df_allsmolts[
    df_allsmolts['LocationCode'].isin(target_locations) |
    df_allsmolts['SiteCode'].isin(target_locations)
]

first_detection = (
    at_target.groupby('FishID')['FirstTS']
    .min()
    .rename('first_target_ts')
    .reset_index()
)

df_filtered = (
    df_allsmolts
    .merge(first_detection, on='FishID', how='inner')
    .query('FirstTS >= first_target_ts')
    .drop(columns='first_target_ts')
    .reset_index(drop=True)
)

# 1,600 unique FishIDs were detected at the target locations
# Records dropped from 146,738 → 15,705 (fish not detected at target locations are excluded entirely, and pre-detection records for qualifying fish are removed)

df_filtered.to_csv('data/all_smolts_filtered_clean.csv', index=False)

# generate an interactive plot with all locations in this dataset
import plotly.express as px

df_plot = df_filtered[['Latitude', 'Longitude', 'LocationCode', 'SiteCode']].dropna(subset=['Latitude', 'Longitude']).drop_duplicates()

fig = px.scatter_map(
    df_plot,
    lat='Latitude',
    lon='Longitude',
    hover_data={'LocationCode': True, 'SiteCode': True, 'Latitude': ':.4f', 'Longitude': ':.4f'},
    zoom=5,
    height=700,
    title='Acoustic Receiver Locations'
)