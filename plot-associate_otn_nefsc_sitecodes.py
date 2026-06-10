# plot OTN and NEFSC sitecodes on a map to visually inspect for co-located sites. This is a precursor to the "nearest neighbour" join in the next script, which will attempt to associate OTN sites with their nearest NEFSC site (if within a reasonable distance threshold).
# then, use a nearest neighbour join to associate OTN sites with their closest NEFSC site, and inspect the distance distribution to determine a reasonable threshold for "co-located" sites. This will help us decide whether to concatenate SiteCodes for nearby sites or keep them separate.

# load the .csv
dat = pd.read_csv("data/dat_otn_nefsc_combined.csv", parse_dates=["DetectDateTime"])

# plot sitecodes from 'dat'
import pandas as pd
import folium

# Unique OTN sites
otn_sites = (
    dat[dat['Source'] == 'OTN']
    [['SiteCode', 'Latitude', 'Longitude']]
    .drop_duplicates()
    .reset_index(drop=True)
)

# Unique NEFSC sites
nefsc_sites = (
    dat[dat['Source'] == 'NEFSC']
    [['SiteCode', 'Latitude', 'Longitude']]
    .drop_duplicates()
    .reset_index(drop=True)
)

# Center map on mean coords of all sites combined
all_sites = pd.concat([otn_sites, nefsc_sites])

m = folium.Map(
    location=[all_sites['Latitude'].mean(), all_sites['Longitude'].mean()],
    zoom_start=8
)

for _, row in otn_sites.iterrows():
    folium.CircleMarker(
        location=[row['Latitude'], row['Longitude']],
        radius=6,
        color='steelblue',
        fill=True,
        fill_color='steelblue',
        fill_opacity=0.8,
        tooltip=f"OTN: {row['SiteCode']}"
    ).add_to(m)

for _, row in nefsc_sites.iterrows():
    folium.CircleMarker(
        location=[row['Latitude'], row['Longitude']],
        radius=6,
        color='orange',
        fill=True,
        fill_color='orange',
        fill_opacity=0.8,
        tooltip=f"NEFSC: {row['SiteCode']}"
    ).add_to(m)

# Legend
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

m.save("data/otn_nefsc_sites_map.html")
m


# inspect neighboring locations of SiteCodes from OTN and NEFSC to see if there are any that are co-located (e.g. within some threshold that we determine below). 
# this will help us decide whether to concatenate SiteCodes for nearby sites or keep them separate in the combined dataset.
import geopandas as gpd
from shapely.geometry import Point

# Build GeoDataFrames for unique sites
gdf_otn = gpd.GeoDataFrame(
    otn_sites,
    geometry=gpd.points_from_xy(otn_sites['Longitude'], otn_sites['Latitude']),
    crs="EPSG:4326"
).to_crs(epsg=32619)  # UTM zone 19N — good for Maine/Nova Scotia, units in metres

gdf_nefsc = gpd.GeoDataFrame(
    nefsc_sites,
    geometry=gpd.points_from_xy(nefsc_sites['Longitude'], nefsc_sites['Latitude']),
    crs="EPSG:4326"
).to_crs(epsg=32619)

# Nearest neighbour join: for each OTN site, find the closest NEFSC site
joined = gpd.sjoin_nearest(
    gdf_otn,
    gdf_nefsc[['SiteCode', 'geometry']],
    how='left',
    distance_col='dist_m'
)

# Inspect the distance distribution before committing to a threshold
joined[['SiteCode_left', 'SiteCode_right', 'dist_m']].sort_values('dist_m').head(20)

# This gives you a table of OTN sites paired with their nearest NEFSC site and the distance in metres. From there you can:
# Inspect the distance distribution — plot a histogram of dist_m to find a natural break that separates "genuinely nearby" from "incidentally closest"
# Apply a threshold — e.g. only concatenate where dist_m < 500 (500 m), leaving distant pairs unchanged:

import matplotlib.pyplot as plt

joined['dist_m'].plot.hist(bins=50)
plt.xlabel('Distance to nearest NEFSC site (m)')
plt.title('OTN → nearest NEFSC distance distribution')
plt.show()

# Rows where OTN and NEFSC sites are co-located (within 500 m)
threshold_m = 500  # adjust based on the distance histogram
matched = joined[joined['dist_m'] <= threshold_m][['SiteCode_left', 'SiteCode_right', 'dist_m']]
matched.to_csv("data/otn_nefsc_sitecode_matches.csv", index=False)

joined['SiteCode_combined'] = joined.apply(
    lambda r: f"{r['SiteCode_left']}_{r['SiteCode_right']}" 
              if r['dist_m'] <= threshold_m 
              else r['SiteCode_left'],
    axis=1
)

# now we make a list of SiteCodes to group together in the combined dataset. This will be used in the next script to concatenate SiteCodes for nearby sites.
groupings = joined.groupby('SiteCode_combined')['SiteCode_left'].apply(list).reset_index()
groupings

matched['SiteCode_new'] = matched['SiteCode_right'].str[:2]
matched.to_csv("data/otn_nefsc_sitecode_matches1.csv", index=False)

nefsc_prefixes = ('FP', 'WP', 'LH', 'DH', 'ER', 'OH', 'MH')
otn_map = matched.set_index('SiteCode_left')['SiteCode_new'].to_dict()

# Default: retain original SiteCode
dat['SiteCode_new'] = dat['SiteCode']

# OTN: map via matched lookup
otn_mask = dat['Source'] == 'OTN'
dat.loc[otn_mask, 'SiteCode_new'] = dat.loc[otn_mask, 'SiteCode'].map(otn_map)

# NEFSC: use first 2 chars if SiteCode starts with a known prefix
nefsc_prefix_mask = (dat['Source'] == 'NEFSC') & dat['SiteCode'].str.startswith(nefsc_prefixes, na=False)
dat.loc[nefsc_prefix_mask, 'SiteCode_new'] = dat.loc[nefsc_prefix_mask, 'SiteCode'].str[:2]

dat[['Source', 'SiteCode', 'SiteCode_new']].drop_duplicates().sort_values(['Source', 'SiteCode']).head(20)

dat.loc[otn_mask & dat['SiteCode_new'].isna(), 'SiteCode_new'] = dat.loc[otn_mask & dat['SiteCode_new'].isna(), 'SiteCode']

# Verify
otn_unmapped_after = dat[otn_mask & dat['SiteCode_new'].isna()]
print(f"OTN rows still unmatched: {len(otn_unmapped_after)}")

dat = dat.sort_values(['Year', 'IDCode', 'DetectDateTime']).reset_index(drop=True)
dat.to_csv("data/dat_otn_nefsc_combined_sitecodes.csv", index=False)

# IDCodes that were detected at least once at an HFX site
hfx_ids = set(dat.loc[dat['SiteCode'].str.startswith('HFX', na=False), 'IDCode'])

# Keep only rows whose IDCode appears in that set
dat = dat[dat['IDCode'].isin(hfx_ids)].reset_index(drop=True)

# Rearrange columns
dat = dat[
    ['Source', 'Year', 'IDCode', 'SiteCode', 'SiteCode_new', 'DetectDateTime', 'Latitude', 'Longitude', 
    'receiver','tagName', 'catalogNumber','unqDetecID', 'ForkLength', 'Weight']
]

dat.to_csv("data/dat_otn_nefsc_combined_sitecodes_hfx.csv", index=False)
