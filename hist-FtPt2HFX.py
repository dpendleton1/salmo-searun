import pandas as pd
import matplotlib.pyplot as plt

# Filter for fish with data in both columns
df_filtered = df_otn.dropna(subset=['MaxDet-FtPoint', 'MinDetect-OTN'])

# Convert to datetime with mixed format handling
df_filtered['MaxDet-FtPoint'] = pd.to_datetime(df_filtered['MaxDet-FtPoint'], format='mixed')
df_filtered['MinDetect-OTN'] = pd.to_datetime(df_filtered['MinDetect-OTN'], format='mixed')

# Calculate time difference in days
df_filtered['time_diff_days'] = (df_filtered['MinDetect-OTN'] - df_filtered['MaxDet-FtPoint']).dt.total_seconds() / (24 * 3600)

# Split by PI
df_noaa = df_filtered[df_filtered['PI'] == 'NOAA']
df_usgs = df_filtered[df_filtered['PI'] == 'USGS']

# Create side-by-side histograms
fig, axes = plt.subplots(1, 2, figsize=(14, 6))

# NOAA histogram
axes[0].hist(df_noaa['time_diff_days'], bins=30, edgecolor='black', color='steelblue')
axes[0].set_xlabel('Time Difference (days)')
axes[0].set_ylabel('Frequency')
axes[0].set_title(f'NOAA Fish (n={len(df_noaa)})')
axes[0].grid(True, alpha=0.3)

# USGS histogram
axes[1].hist(df_usgs['time_diff_days'], bins=30, edgecolor='black', color='coral')
axes[1].set_xlabel('Time Difference (days)')
axes[1].set_ylabel('Frequency')
axes[1].set_title(f'USGS Fish (n={len(df_usgs)})')
axes[1].grid(True, alpha=0.3)

plt.suptitle('Time Between MaxDet-FtPoint and MinDetect-OTN', fontsize=14, y=1.02)
plt.tight_layout()
plt.show()

# Summary statistics for both groups
print("NOAA Summary:")
print(df_noaa['time_diff_days'].describe())
print("\nUSGS Summary:")
print(df_usgs['time_diff_days'].describe())