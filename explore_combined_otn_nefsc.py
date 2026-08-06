import pandas as pd

out_dir = Path("data/output_files")

dat = pd.read_csv(out_dir / "dat_otn_nefsc_combined_sitecodes_hfx.csv")

dat.head()

# number of unique IDCodes at FP
dat[dat['SiteCode_new'] == 'FP']['IDCode'].nunique()

# number of unique IDCodoes that were never at FP
fp_ids = dat[dat['SiteCode_new'] == 'FP']['IDCode'].unique()
dat[~dat['IDCode'].isin(fp_ids)]['IDCode'].nunique()


# list of unique IDCodes that were never at FP
no_fp = dat[~dat['IDCode'].isin(fp_ids)]['IDCode'].unique()
print(f"Count: {len(no_fp)}")
print(sorted(no_fp))

dat_no_fp = dat[~dat['IDCode'].isin(fp_ids)].reset_index(drop=True)
print(dat_no_fp.shape)
dat_no_fp

dat[dat['SiteCode_new'] != 'FP']['IDCode'].nunique()

dat['IDCode'].nunique()
