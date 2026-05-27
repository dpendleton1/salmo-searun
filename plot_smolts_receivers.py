# generate an interactive plot with all locations in this dataset
import plotly.express as px

df_plot = df_filtered[['Latitude', 'Longitude', 'SiteCode']].dropna(subset=['Latitude', 'Longitude']).drop_duplicates()

fig = px.scatter_map(
    df_plot,
    lat='Latitude',
    lon='Longitude',
    hover_data={'SiteCode': True, 'Latitude': True, 'Longitude': True},
    zoom=5,
    height=700,
    title='Acoustic Receiver Locations'
)
fig