import polars as pl

# Read the CSV file
df = pl.read_csv('tidbits1325.csv')

# Display basic information about the dataset
print(f"Dataset shape: {df.shape[0]} rows × {df.shape[1]} columns")
print(f"\nColumn names and types:")
print(df.schema)

# Create a summary table
df.describe()