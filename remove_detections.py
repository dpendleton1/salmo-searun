import polars as pl
df = pl.read_csv('/data/Smolts 2013-15.csv')
df_filtered = df.filter(pl.col('Event') != 'Detection')