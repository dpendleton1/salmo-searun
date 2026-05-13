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