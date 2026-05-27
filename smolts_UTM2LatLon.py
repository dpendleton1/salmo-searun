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
