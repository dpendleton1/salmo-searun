import pandas as pd

df_allsmolts = pd.read_csv('data/allsmolts.csv', low_memory=False)

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

# Rename some columns
#df_allsmolts = df_allsmolts.rename(columns={'IDCode': 'PingerIDCode'})
df_allsmolts = df_allsmolts.rename(columns={'RKM': 'RiverKm'})

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

# # remove dates before 2012
# df_allsmolts = df_allsmolts[df_allsmolts['Period'] > '2011-12-31 23:59:59'].reset_index(drop=True)
# df_allsmolts.shape

# # create a new column the concatenates Codespace and IDCode. These two columns are supposed to be concatenated in the TagId column, but that's not always the case.
# df_allsmolts['TagCode'] = df_allsmolts['Codespace'] + '-' + df_allsmolts['IDCode'].astype(str)

# tagtype and Species only contain one value 'Acoustic' and 'ATS' so we can remove those columns
#df_allsmolts = df_allsmolts.drop(columns=['Period','tagtype', 'Species','Frequency','avgPower','AntennaID','LocationCode','UTMZone','AltFishID'])


#####################################################################################################

#Looking at 'allsmolts.csv', I want to remove all records for each 'IDCode' that were not detected 
# at one of the following 'SiteCode' that have one of the following prefixes: 
# 'FP','FTPN','WPLP','WP-','WP0','DH','LH','ER','MH','OH'. If a particular 'IDCode' was detected 
# at one of the 'SiteCode' in my list, then I want to keep all other detections for that 'IDCode', 
# even if they have a 'SiteCode' not contained in my list.

prefixes_to_keep = ('FP', 'FTPN', 'WPLP', 'WP-', 'WP0', 'DH', 'LH', 'ER', 'MH', 'OH')

# IDCodes detected at least once at a SiteCode matching one of the prefixes
valid_ids = df_allsmolts.loc[
    df_allsmolts['SiteCode'].str.startswith(prefixes_to_keep, na=False), 'IDCode'
].unique()

# Keep all rows for those IDCodes
df_filtered = df_allsmolts[df_allsmolts['IDCode'].isin(valid_ids)].reset_index(drop=True)
df_filtered.shape

# Remove records for 'IDCode' that occurred before the first detection at a target 'SiteCode'

# Find the first detection timestamp at a target SiteCode for each IDCode
first_target_ts = (
    df_filtered[df_filtered['SiteCode'].str.startswith(prefixes_to_keep, na=False)]
    .groupby('IDCode')['FirstTS']
    .min()
    .rename('first_target_ts')
)

# Merge back and keep only rows at or after that timestamp
df_filtered = (
    df_filtered
    .merge(first_target_ts, on='IDCode', how='left')
    .query('FirstTS >= first_target_ts')
    .drop(columns='first_target_ts')
    .reset_index(drop=True)
)

df_filtered.shape

df_filtered.to_csv('data/all_smolts_filtered_clean1.csv', index=False)

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