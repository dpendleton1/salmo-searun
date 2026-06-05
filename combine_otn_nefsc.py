# join datasets

#from combine_allyears_oceanOnly import dat_nefsc_pb_forward
#from combine_PN_matched import dat_otn

import pandas as pd

dat_nefsc_pb_forward = pd.read_csv("data/Penobscot Access Databases/csv_export/dat_nefsc_pb_forward.csv", parse_dates=["DetectDateTime"])
dat_otn = pd.read_csv("data/NOAA Halifax Detection Data/PN/dat_otn.csv", parse_dates=["DetectDateTime"])

merged = pd.concat([dat_otn, dat_nefsc_pb_forward], ignore_index=True, sort=False)
merged['DetectDateTime'] = pd.to_datetime(merged['DetectDateTime'], format='ISO8601')
merged = merged.sort_values(['Year', 'IDCode', 'DetectDateTime']).reset_index(drop=True)

print(merged.shape)
print(merged.columns.tolist())
merged.head()


# Check how many rows have the same SiteCode and DetectDateTime but different Source
dupes = (
    merged[merged['Source'].isin(['OTN', 'NEFSC'])]
    .groupby(['SiteCode', 'DetectDateTime'])
    .filter(lambda x: x['Source'].nunique() > 1)
)
print(f"Rows with matching SiteCode+DetectDateTime but different Source: {len(dupes)}")
dupes[['SiteCode', 'DetectDateTime', 'Source', 'IDCode']].sort_values(['SiteCode', 'DetectDateTime']).head(20)

merged.to_csv("data/dat_otn_nefsc.csv", index=False)

#NEXT WE NEED TO GROUP SITECODES WITHIN PB. NOT SURE BEST PLACE TO DO THIS.
# AFTER THAT WE NEED TO REMOVE FISH THAT NEVER GOT TO HALIFAX


# exploration
# visualize SiteCode with prefix = 'PBN', because these are intriguing
# there are other sitecodes that are not HFX also. 
# lets have a look
import folium

# Unique OTN sites
otn_sites = (
    merged[merged['Source'] == 'OTN']
    [['SiteCode', 'Latitude', 'Longitude']]
    .drop_duplicates()
    .reset_index(drop=True)
)

# Unique NEFSC sites
nefsc_sites = (
    merged[merged['Source'] == 'NEFSC']
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

m.save("otn_nefsc_sites_map.html")
m
