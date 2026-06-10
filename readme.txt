# salmo-searun readme

# scripts to run, and in the following order
**. combine_nefsc_access_files.py
-this script combines the NEFSC Access Database files that Jim provided
-this script produces:
    -"dat_nefsc_latlon_4reload.csv" #dataset after lat/lon are produced. this operation takes a long time, so instead of recomputing lat/lon you can simply reload this file, however you may be missing a few variables created prior to this point
    -"dat_nefsc.csv" #sorted dataset with reduced number of columns, includes all SiteCodes
    -"dat_nefsc_pb_forward.csv" #dataset containing only IDCodes that passed through SiteCodes in PenBay and all detections after that point in time

**. plot_SiteCodes_nefsc.py
-this script plots NEFSC receiver stations from "dat_nefsc_pb_forward.csv"
-this script produces "site_map_nefsc.html" showing locations and River Km for SiteCodes

combine_otn_pn_matched_files.py
-this script combines otn and nefsc

**. combine_otn_nefsc.py
-this script combines the "pbn_matched_detections_YEAR.csv" files that were downloaded from OTN
-this script produces "dat_otn.csv" #dataset containing sorted and OTN dataset with necessary columns

**. combine_otn_nefsc.py
-this script merges the nefsc and otn 'combined' files created above
-this script produces "dat_otn_nefsc_combined.csv" which is a combined nefsc and otn file. no duplicates were found. the file is sorted by ['Year', 'IDCode', 'DetectDateTime'] 

**. plot-associate_otn_nefsc_sitecodes.py
-this script plots OTN and NEFSC sitecodes on a map for visual inspection
    -"otn_nefsc_sites_map.html"
-then it calculates distance between neighboring SiteCodes so I can determine which SiteCodes should be combined
    -"otn_nefsc_sitecode_matches.csv" contains OTN and NEFSC SiteCodes and distances (if < 500 m)
    
