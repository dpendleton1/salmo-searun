import pandas as pd

df_allsmolts = pd.read_csv('data/USGS/allsmolts.csv', low_memory=False)
df_allsmolts.shape

# make data types within columns consistent. they are not consistent because I pasted two datasets together.
# datetimes: parse with mixed formats, then convert back to string in consistent format
df_allsmolts['Period'] = pd.to_datetime(df_allsmolts['Period'], format='mixed')
df_allsmolts['FirstTS'] = pd.to_datetime(df_allsmolts['FirstTS'], format='mixed')
df_allsmolts['LastTS'] = pd.to_datetime(df_allsmolts['LastTS'], format='mixed')
df_allsmolts['Year'] = df_allsmolts['Period'].dt.year

# TagId: coerce to numeric (Int64 to support NaN)
df_allsmolts['TagId'] = pd.to_numeric(df_allsmolts['TagId'], errors='coerce').astype('Int64')

# SensorType: replace blank/whitespace strings with NaN
df_allsmolts['SensorType'] = df_allsmolts['SensorType'].str.strip().replace('', pd.NA)

# RxID: coerce to numeric (Int64 to support NaN)
df_allsmolts['RxID'] = pd.to_numeric(df_allsmolts['RxID'], errors='coerce').astype('Int64')

# UTMZone: cast float to Int64
df_allsmolts['UTMZone'] = df_allsmolts['UTMZone'].astype('Int64')

# Rename some columns
df_allsmolts = df_allsmolts.rename(columns={'RKM': 'RiverKm'})

# IDCode is not unique. Create a new column that combines Year and IDCode to create a unique identifier for each fish-year combination.
df_allsmolts['YearIDCode'] = (df_allsmolts['Year'].astype(str) + df_allsmolts['IDCode'].astype(str)).astype(int)

# Verify consistent format in all columns
for col in df_allsmolts.columns:
    dtype = df_allsmolts[col].dtype
    n_unique = df_allsmolts[col].nunique()
    sample = df_allsmolts[col].dropna().head(3).tolist()
    print(f"{col:20s} | {str(dtype):10s} | unique={n_unique:6} | sample={sample}")

# create latitude and longitude columns from easting, northing and UTMZone
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
df_allsmolts.shape

# Drop columns (some that you just modified, but we won't need them for this analysis)
df_allsmolts.drop(columns=['tagtype','Species','FishID','TagId','SensorType',
'avgSensorValue','avgComputedValue','Frequency','avgPower','AntennaID','RxID','DeploymentUID',
'LocationCode','UTMZone','AltFishID'], inplace=True)

# Rearrange columns
df_allsmolts = df_allsmolts[['Year', 'YearIDCode', 'IDCode', 'Period', 'FirstTS', 'LastTS', 
'Event','SiteCode','Easting','Northing','Latitude','Longitude','pings','RiverKm']]
df_allsmolts.shape

# remove rows with no-data in Easting, Northing and SiteCode
df_allsmolts = df_allsmolts.dropna(subset=['Easting', 'Northing', 'SiteCode']).reset_index(drop=True)
df_allsmolts.shape

# remove dates before 2012
df_allsmolts = df_allsmolts[df_allsmolts['Period'] > '2011-12-31 23:59:59'].reset_index(drop=True)
df_allsmolts.shape

# sort by Year, YearIDCode and FirstTS
df_allsmolts = df_allsmolts.sort_values(['Year', 'YearIDCode', 'IDCode', 'FirstTS']).reset_index(drop=True)

# keep only the first and last detection for each IDCode at each SiteCode, and sum the pings
# NOTE: this drops columns not listed below.
df_allsmolts = (
    df_allsmolts
    .groupby(['Year', 'YearIDCode', 'IDCode', 'SiteCode'], as_index=False)
    .agg(
        FirstTS=('FirstTS', 'min'),
        LastTS=('LastTS', 'max'),
        pings=('pings', 'sum'),
        Event=('Event', 'first'),
        Easting=('Easting', 'first'),
        Northing=('Northing', 'first'),
        Latitude=('Latitude', 'first'),
        Longitude=('Longitude', 'first'),
        RiverKm=('RiverKm', 'first'),
    )
)
df_allsmolts.shape
df_allsmolts.head()

# [NECESSARY] sort by Year, YearIDCode and FirstTS
df_allsmolts = df_allsmolts.sort_values(['Year', 'YearIDCode', 'IDCode', 'FirstTS']).reset_index(drop=True)

# list all the unique SiteCodes in this dataset
SiteCodes_before_filter = sorted(df_allsmolts['SiteCode'].unique())
# sorted returns a list, must wrap it in pd.Series to use to_csv method. Also add header for clarity.
pd.Series(SiteCodes_before_filter).to_csv('data/USGS/output/SiteCodes_before_filter.csv', index=False, header=['SiteCode'])

# begin filtering to keep only IDCodes detected at certain SiteCodes, and all their detections at SiteCodes encountered after the first encounter of an acceptable SiteCode.
SiteCodes_to_keep = ['FP-03', 'FP01','FP02','FP03','FP04','FP05','FP06','FTPNT',
 'WP-03','WP-04','WP-05','WP01','WP02','WP03','WP04','WP05',
 'DH01', 'DH01A','DH02','DH02A','DH03','DH03A','DH04','DH04A',
 'DH05','DH05A','DH06','DH06A','DH07','DH07A','DH08','DH09',
 'DH10','DH11','DH12','DH13','DH14',
 'ER02',
 'LH01','LH02','LH03','LH04','LH05','LH06','LH07','LH08','LH09',
 'LH10','LH11','LH12',
 'MH01', 'MH02','MH03','MH03A','MH04','MH04A','MH05','MH05A','MH06',
 'MH06A','MH07','MH07A','MH08','MH08A','MH09','MH09A','MH10','MH11',
 'OH01','OH01A','OH02','OH02A','OH03','OH03A','OH04','OH04A','OH05',
 'OH06','OH06A','OH07','OH07A','OH08','OH08A','OH09','OH09A','OH10',
 'OH10A','OH11','OH11A','OH12','OH12A','OH13','OH13A','OH14']

first_detection = (
    df_allsmolts.loc[df_allsmolts['SiteCode'].isin(SiteCodes_to_keep)]
    .groupby(['Year', 'YearIDCode', 'IDCode'])['FirstTS']
    .min()
    .rename('first_prefix_ts')
)
first_detection.to_csv('data/USGS/output/first_detection.csv', index=True)

df_filtered = (
    df_allsmolts
    .join(first_detection, on=['Year', 'YearIDCode', 'IDCode'], how='left')
    .dropna(subset=['first_prefix_ts'])
    .query('FirstTS >= first_prefix_ts')
    .drop(columns='first_prefix_ts')
    .reset_index(drop=True)
)

# list all the unique SiteCodes in this dataset
SiteCodes_after_filter = sorted(df_filtered['SiteCode'].unique())
# sorted returns a list, must wrap it in pd.Series to use to_csv method. Also add header for clarity.
pd.Series(SiteCodes_after_filter).to_csv('data/USGS/output/SiteCodes_after_filter.csv', index=False, header=['SiteCode'])

# list all the first SiteCode for each IDCode in the filtered dataset
site_sequence = (
    df_filtered
    .sort_values(['Year', 'YearIDCode', 'IDCode', 'FirstTS'])
    .groupby(['Year', 'YearIDCode', 'IDCode'], as_index=False)
    .agg(SiteCodes=('SiteCode', list))
)
site_sequence.to_csv('data/USGS/output/site_sequence.csv', index=False)

# save the final filtered file to .csv
df_filtered.to_csv('data/USGS/output/df_allsmolts_filtered.csv', index=False)

# generate an interactive plot with all locations in this dataset
import plotly.express as px
df_plot = df_filtered[['Latitude', 'Longitude', 'SiteCode']].dropna(subset=['Latitude', 'Longitude']).drop_duplicates()
fig = px.scatter_map(
    df_plot,
    lat='Latitude',
    lon='Longitude',
    hover_data={'SiteCode': True, 'Latitude': True, 'Longitude': True},
    zoom=5,
    height=700,
    title='Acoustic Receiver Locations'
)
fig

# list all the unique SiteCodes in this dataset that start with 'HFX', and the unique IDCodes associated with those SiteCodes
hfx_ids = df_filtered.loc[df_filtered['SiteCode'].str.startswith('HFX'), 'YearIDCode'].unique()
# filter the dataset to keep only rows with those IDCodes, and save to .csv
df_filtered_PN2HFX = df_filtered[df_filtered['YearIDCode'].isin(hfx_ids)].reset_index(drop=True)
df_filtered_PN2HFX.shape
df_filtered_PN2HFX.to_csv('data/USGS/output/df_filtered_PN2HFX.csv', index=False)

# list all the first SiteCode for each IDCode in the filtered dataset
site_sequence_PN2HFX = (
    df_filtered_PN2HFX
    .sort_values(['Year', 'YearIDCode', 'IDCode', 'FirstTS'])
    .groupby(['Year', 'YearIDCode', 'IDCode'], as_index=False)
    .agg(SiteCodes=('SiteCode', list))
)
site_sequence_PN2HFX.to_csv('data/USGS/output/site_sequence_PN2HFX.csv', index=False)

# generate an interactive plot with all locations in this dataset
import plotly.express as px
df_plot = df_filtered_PN2HFX[['Latitude', 'Longitude', 'SiteCode']].dropna(subset=['Latitude', 'Longitude']).drop_duplicates()
fig = px.scatter_map(
    df_plot,
    lat='Latitude',
    lon='Longitude',
    hover_data={'SiteCode': True, 'Latitude': True, 'Longitude': True},
    zoom=5,
    height=700,
    title='Acoustic Receiver Locations'
)
fig

# test a particular IDCode, for debugging or exploration
df_filtered[df_filtered['IDCode'] == 9861][['IDCode', 'SiteCode', 'FirstTS']]