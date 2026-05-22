import pandas as pd
import folium
from pyproj import Transformer

# Deduplicate to one row per SiteCode
sites = (
    summary
    .dropna(subset=["RefUTMEast", "RefUTMNorth"])
    .assign(RiverKm=lambda df: df["RiverKm"].replace(-999.99, pd.NA))
    .query("RefUTMNorth < 6_000_000")   # filter implausible northings
    .groupby("SiteCode", as_index=False)
    .agg(RefUTMEast=("RefUTMEast", "first"), RefUTMNorth=("RefUTMNorth", "first"),
         RiverKm=("RiverKm", "first"))
)

# Convert UTM Zone 19N → lat/lon (WGS84)
transformer = Transformer.from_crs("EPSG:32619", "EPSG:4326", always_xy=True)
sites["lon"], sites["lat"] = transformer.transform(
    sites["RefUTMEast"].values,
    sites["RefUTMNorth"].values
)

# Build folium map centred on mean position
m = folium.Map(
    location=[sites["lat"].mean(), sites["lon"].mean()],
    zoom_start=9,
    tiles="OpenStreetMap"
)

for _, row in sites.iterrows():
    folium.CircleMarker(
        location=[row["lat"], row["lon"]],
        radius=6,
        color="steelblue",
        fill=True,
        fill_opacity=0.8,
        popup=folium.Popup(
            f"<b>{row['SiteCode']}</b><br>RiverKm: {row['RiverKm']}<br>"
            f"UTM E: {row['RefUTMEast']:.0f}<br>UTM N: {row['RefUTMNorth']:.0f}",
            max_width=200
        ),
        tooltip=row["SiteCode"]
    ).add_to(m)

m.save("data/Penobscot Access Databases/csv_export/site_map.html")
m
