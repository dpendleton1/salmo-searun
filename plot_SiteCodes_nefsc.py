import pandas as pd
import folium
from pyproj import Transformer

summary = dat_nefsc_pb_forward

# Deduplicate to one row per SiteCode
sites = (
    summary
    .dropna(subset=["Longitude", "Latitude"])
    .assign(RiverKm=lambda df: df["RiverKm"].replace(-999.99, pd.NA))
    .groupby("SiteCode", as_index=False)
    .agg(Longitude=("Longitude", "first"), Latitude=("Latitude", "first"),
         RiverKm=("RiverKm", "first"))
)

# Build folium map centred on mean position
m = folium.Map(
    location=[sites["Latitude"].mean(), sites["Longitude"].mean()],
    zoom_start=9,
    tiles="OpenStreetMap"
)

for _, row in sites.iterrows():
    folium.CircleMarker(
        location=[row["Latitude"], row["Longitude"]],
        radius=6,
        color="steelblue",
        fill=True,
        fill_opacity=0.8,
        popup=folium.Popup(
            f"<b>{row['SiteCode']}</b><br>RiverKm: {row['RiverKm']}<br>"
            f"UTM E: {row['Longitude']:.0f}<br>UTM N: {row['Latitude']:.0f}",
            max_width=200
        ),
        tooltip=row["SiteCode"]
    ).add_to(m)

m.save("data/Penobscot Access Databases/csv_export/site_map_nefsc.html")
m

