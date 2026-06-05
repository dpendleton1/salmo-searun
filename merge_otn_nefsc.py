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

