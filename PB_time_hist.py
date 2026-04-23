import pandas as pd
import matplotlib.pyplot as plt

# Load OTN data
df_otn = pd.read_csv('data/OTN_2008-2015.csv')

# Filter for fish with data in both columns
df_both = df_otn.dropna(subset=['MinDet-FtPoint', 'MaxDet-PenBayOuter'])

# Convert to datetime
df_both['MinDet-FtPoint'] = pd.to_datetime(df_both['MinDet-FtPoint'])
df_both['MaxDet-PenBayOuter'] = pd.to_datetime(df_both['MaxDet-PenBayOuter'])

# Calculate time difference in days
df_both['time_diff_days'] = (df_both['MaxDet-PenBayOuter'] - df_both['MinDet-FtPoint']).dt.total_seconds() / (24 * 3600)

# Create histogram
plt.figure(figsize=(10, 6))
plt.hist(df_both['time_diff_days'], bins=30, edgecolor='black')
plt.xlabel('Time Difference (days)')
plt.ylabel('Frequency')
plt.title('Time Between MinDet-FtPoint and MaxDet-PenBayOuter')
plt.grid(True, alpha=0.3)
plt.show()

# Summary statistics
df_both['time_diff_days'].describe()