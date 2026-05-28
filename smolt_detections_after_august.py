# plot smolts detections after Aug 1 by year
df_allsmolts['FirstTS_dt'] = pd.to_datetime(df_allsmolts['FirstTS'], format='mixed')

(
    df_allsmolts[
        (df_allsmolts['FirstTS_dt'].dt.month >= 8) &
        (df_allsmolts['Event'] == 'Detection')
    ]
    .assign(Year=df_allsmolts['FirstTS_dt'].dt.year)
    .groupby('Year')
    .size()
    .rename('n_detections')
    .reset_index()
)
