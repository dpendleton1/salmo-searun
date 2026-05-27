# determine SiteCodes that are located within the approximate bounds of Penobscot Bay, Maine
from shapely.geometry import Point, Polygon

# Approximate (longitude, latitude) coordinates bounding Penobscot Bay
# Belfast -> Stockton Springs -> Penobscot (town) -> Stonington -> Owls Head -> Rockland -> Belfast
penobscot_bay = Polygon([
    (-69.0070, 44.4248),  # Belfast
    (-68.8607, 44.4923),  # Stockton Springs
    (-68.7944, 44.5548),  # Penobscot
    (-68.6628, 44.1571),  # Stonington
    (-69.0785, 44.0762),  # Owls Head
    (-69.1094, 44.1037),  # Rockland
    (-69.0070, 44.4248),  # Belfast (close polygon)
])

sites_in_bay = (
    df_allsmolts
    .dropna(subset=['Latitude', 'Longitude'])
    .loc[lambda df: df.apply(
        lambda row: penobscot_bay.contains(Point(row['Longitude'], row['Latitude'])), axis=1
    ), 'SiteCode']
    .unique()
    .tolist()
)

sites_in_bay
sites_in_bay_sorted = sorted(sites_in_bay)
sites_in_bay_sorted