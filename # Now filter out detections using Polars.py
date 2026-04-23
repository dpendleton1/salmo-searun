# Now filter out detections using Polars
import polars as pl

df = pl.df('Smolts 2013-15.csv')
#df_filtered = df.filter(pl.col('Event') != 'Detection')
df_filtered = df.filter(pl.col('Event') != 'Detection')

df.head()