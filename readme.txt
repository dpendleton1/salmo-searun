# salmo-searun readme

# scripts to run, and in the following order
**. 1_combine_nefsc_access_files.py
-this script combines the NEFSC Access Database files that Jim provided
-this script produces:
    -"dat_nefsc.csv" #sorted dataset with reduced number of columns, includes all SiteCodes
    -"dat_nefsc_pb_forward.csv" #dataset containing only IDCodes that passed through SiteCodes in PenBay and all detections after that point in time
    -"dat_nefsc_pb_forward_deploy.csv" same as "dat_nefsc_pb_forward.csv" but only keeps 'deploy', this eliminating redundancy
    -"dat_nefsc_pb_forward_deploy_latlon.csv" same as "dat_nefsc_pb_forward_deploy.csv", but converts lat/lon to decimal degrees

**. 2_plot_SiteCodes_nefsc.py
-this script plots NEFSC receiver stations from "dat_nefsc_pb_forward_deploy.csv"
-this script produces "site_map_nefsc.html" showing locations and River Km for SiteCodes

**. 3_combine_otn_nefsc.py
-this script merges the nefsc and otn files created above
    -dat_otn & dat_nefsc_pb_forward_deploy_latlon
-this script produces "dat_otn_nefsc_combined.csv" which is a combined nefsc and otn file. no duplicates were found. the file is sorted by ['Year', 'IDCode', 'DetectDateTime'] 

**. 4_plot_associate_otn_nefsc_sitecodes.py
-this script plots OTN and NEFSC sitecodes on a map for visual inspection
    -"otn_nefsc_sites_map.html"
-filters out far flung records based on Lat/Long, saves a file of the records that are removed_records
-additionally, calculates distance between neighboring SiteCodes to determine which SiteCodes should be combined
    -"otn_nefsc_sitecode_matches.csv" contains OTN and NEFSC SiteCodes and distances (if < 500 m)
    -there are still some issues here, for example, look for OTN SiteCodes and see how detections flow in time. 
        -they may be off by seconds, but locations appear to be the same. Unclear why this is happening. 
        -is there a time error coming from OTN?

    
