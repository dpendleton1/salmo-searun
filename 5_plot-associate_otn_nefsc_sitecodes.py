"""
Map and Associate OTN and NEFSC Receiver Site Codes

This script maps unique OTN and NEFSC receiver locations, performs a spatial
nearest-neighbor join to associate OTN sites with nearby NEFSC array stations,
visualizes the distance distribution, and standardizes site codes across both data
sources.
"""

from pathlib import Path

import folium
import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd

# -----------------------------------------------------------------------------
# Configuration and Data Loading
# -----------------------------------------------------------------------------

out_dir = Path("data/output_files")
dat = pd.read_csv(
    out_dir / "dat_otn_nefsc_combined.csv", parse_dates=["DetectDateTime"]
)

# Extract unique site locations for each data source
otn_sites = (
    dat[dat["Source"] == "OTN"][["SiteCode", "Latitude", "Longitude"]]
    .drop_duplicates()
    .reset_index(drop=True)
)

nefsc_sites = (
    dat[dat["Source"] == "NEFSC"][["SiteCode", "Latitude", "Longitude"]]
    .drop_duplicates()
    .dropna(subset=["Latitude", "Longitude"])
    .reset_index(drop=True)
)

# -----------------------------------------------------------------------------
# Interactive Map Generation
# -----------------------------------------------------------------------------

all_sites = pd.concat([otn_sites, nefsc_sites])
m = folium.Map(
    location=[all_sites["Latitude"].mean(), all_sites["Longitude"].mean()],
    zoom_start=8,
)

for _, row in otn_sites.iterrows():
    folium.CircleMarker(
        location=[row["Latitude"], row["Longitude"]],
        radius=6,
        color="steelblue",
        fill=True,
        fill_color="steelblue",
        fill_opacity=0.8,
        tooltip=f"OTN: {row['SiteCode']}",
    ).add_to(m)

for _, row in nefsc_sites.iterrows():
    folium.CircleMarker(
        location=[row["Latitude"], row["Longitude"]],
        radius=6,
        color="orange",
        fill=True,
        fill_color="orange",
        fill_opacity=0.8,
        tooltip=f"NEFSC: {row['SiteCode']}",
    ).add_to(m)

# Add map legend
legend_html = """
<div style="position: fixed; bottom: 30px; left: 30px; z-index: 1000;
     background-color: white; padding: 10px 15px; border-radius: 6px;
     border: 1px solid grey; font-size: 13px;">
  <b>Source</b><br>
  <span style="color:steelblue;">&#9679;</span> OTN<br>
  <span style="color:orange;">&#9679;</span> NEFSC
</div>
"""
m.get_root().html.add_child(folium.Element(legend_html))
m.save(out_dir / "otn_nefsc_sites_map.html")

# -----------------------------------------------------------------------------
# Spatial Nearest-Neighbor Association
# -----------------------------------------------------------------------------

# Convert to projected CRS (UTM Zone 19N, units in meters) for spatial joins
gdf_otn = gpd.GeoDataFrame(
    otn_sites,
    geometry=gpd.points_from_xy(otn_sites["Longitude"], otn_sites["Latitude"]),
    crs="EPSG:4326",
).to_crs(epsg=32619)

gdf_nefsc = gpd.GeoDataFrame(
    nefsc_sites,
    geometry=gpd.points_from_xy(
        nefsc_sites["Longitude"], nefsc_sites["Latitude"]
    ),
    crs="EPSG:4326",
).to_crs(epsg=32619)

# Find nearest NEFSC site for each OTN site
joined = gpd.sjoin_nearest(
    gdf_otn,
    gdf_nefsc[["SiteCode", "geometry"]],
    how="left",
    distance_col="dist_m",
)

# Plot distance distribution
joined["dist_m"].plot.hist(bins=50)
plt.xlabel("Distance to nearest NEFSC site (m)")
plt.title("OTN → nearest NEFSC distance distribution")
plt.show()

# Apply distance threshold (500m) for co-located sites
threshold_m = 500
matched = joined[joined["dist_m"] <= threshold_m][
    ["SiteCode_left", "SiteCode_right", "dist_m"]
]
matched.to_csv(out_dir / "otn_nefsc_sitecode_matches.csv", index=False)

# -----------------------------------------------------------------------------
# Site Code Standardization and Export
# -----------------------------------------------------------------------------

matched["SiteCode_new"] = matched["SiteCode_right"].str[:2]
matched.to_csv(out_dir / "otn_nefsc_sitecode_matches1.csv", index=False)

nefsc_prefixes = ("FP", "WP", "LH", "DH", "ER", "OH", "MH")
otn_map = matched.set_index("SiteCode_left")["SiteCode_new"].to_dict()

# Standardize site codes
dat["SiteCode_new"] = dat["SiteCode"]

otn_mask = dat["Source"] == "OTN"
dat.loc[otn_mask, "SiteCode_new"] = dat.loc[otn_mask, "SiteCode"].map(otn_map)

nefsc_prefix_mask = (dat["Source"] == "NEFSC") & dat[
    "SiteCode"
].str.startswith(nefsc_prefixes, na=False)
dat.loc[nefsc_prefix_mask, "SiteCode_new"] = dat.loc[
    nefsc_prefix_mask, "SiteCode"
].str[:2]

dat.loc[otn_mask & dat["SiteCode_new"].isna(), "SiteCode_new"] = dat.loc[
    otn_mask & dat["SiteCode_new"].isna(), "SiteCode"
]

dat = dat.sort_values(["Year", "IDCode", "DetectDateTime"]).reset_index(drop=True)
dat.to_csv(out_dir / "dat_otn_nefsc_combined_sitecodes.csv", index=False)

# Filter for IDs detected at least once at an HFX site
hfx_ids = set(
    dat.loc[dat["SiteCode"].str.startswith("HFX", na=False), "IDCode"]
)
dat = dat[dat["IDCode"].isin(hfx_ids)].reset_index(drop=True)

# Rearrange columns and export final filtered dataset
dat = dat[
    [
        "Source",
        "Year",
        "IDCode",
        "SiteCode",
        "SiteCode_new",
        "DetectDateTime",
        "Latitude",
        "Longitude",
        "receiver",
        "tagName",
        "catalogNumber",
        "unqDetecID",
        "ForkLength",
        "Weight",
    ]
]
dat.to_csv(out_dir / "dat_otn_nefsc_combined_sitecodes_hfx.csv", index=False)
