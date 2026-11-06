"""
Plot NEFSC Acoustic Receiver Site Locations

This script loads the processed deployment dataset (produced by '1_combine_nefsc_access_files.py'), 
extracts unique SiteCode coordinates, and generates an interactive Folium map showing receiver locations
with popups and tooltips.
"""

import os
from pathlib import Path

import folium
import pandas as pd

# -----------------------------------------------------------------------------
# Configuration and Data Loading
# -----------------------------------------------------------------------------

out_dir = Path("data/output_files")
summary = dat_nefsc_pb_forward_deploy #this variable contains lat & lon

# Extract unique receiver sites with valid coordinates. From this, we will plot the position of each SiteCode in the dataset. The locations may vary a small amount due to different deployments of receivers
sites = (
    summary.dropna(subset=["Longitude", "Latitude"])
    .assign(RiverKm=lambda df: df["RiverKm"].replace(-999.99, pd.NA))
    .groupby("SiteCode", as_index=False)
    .agg(
        Longitude=("Longitude", "first"),
        Latitude=("Latitude", "first"),
        RiverKm=("RiverKm", "first"),
    )
)

# -----------------------------------------------------------------------------
# Interactive Map Generation
# -----------------------------------------------------------------------------

# Initialize map centered on the mean spatial position
m = folium.Map(
    location=[sites["Latitude"].mean(), sites["Longitude"].mean()],
    zoom_start=9,
    tiles="OpenStreetMap",
)

# Add circle markers for each receiver site
for _, row in sites.iterrows():
    folium.CircleMarker(
        location=[row["Latitude"], row["Longitude"]],
        radius=6,
        color="steelblue",
        fill=True,
        fill_opacity=0.8,
        popup=folium.Popup(
            f"<b>{row['SiteCode']}</b><br>"
            f"RiverKm: {row['RiverKm']}<br>"
            f"Lat: {row['Latitude']:.4f}<br>"
            f"Lon: {row['Longitude']:.4f}",
            max_width=200,
        ),
        tooltip=row["SiteCode"],
    ).add_to(m)

# Save and render map
m.save(os.path.join(out_dir, "site_map_nefsc.html"))
m
