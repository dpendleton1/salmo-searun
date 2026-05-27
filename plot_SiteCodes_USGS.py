import folium

# Deduplicate to one row per SiteCode
sites = (
    df_allsmolts
    .dropna(subset=['Latitude', 'Longitude'])
    .groupby('SiteCode', as_index=False)
    .agg(
        Latitude=('Latitude', 'first'),
        Longitude=('Longitude', 'first'),
        RiverKm=('RiverKm', 'first'),
        Easting=('Easting', 'first'),
        Northing=('Northing', 'first'),
    )
)

# Build folium map centred on mean position
m = folium.Map(
    location=[sites['Latitude'].mean(), sites['Longitude'].mean()],
    zoom_start=9,
    tiles='OpenStreetMap'
)

for _, row in sites.iterrows():
    folium.CircleMarker(
        location=[row['Latitude'], row['Longitude']],
        radius=6,
        color='steelblue',
        fill=True,
        fill_opacity=0.8,
        popup=folium.Popup(
            f"<b>{row['SiteCode']}</b><br>RiverKm: {row['RiverKm']}<br>"
            f"UTM E: {row['Easting']:.0f}<br>UTM N: {row['Northing']:.0f}",
            max_width=200
        ),
        tooltip=row['SiteCode']
    ).add_to(m)

m.save('data/site_map_USGS1.html')
m

