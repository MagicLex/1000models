import hopsworks
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Connect to Hopsworks
project = hopsworks.login()
fs = project.get_feature_store()

# Generate new part-location combinations
sp_ids = [2000001, 2000002, 2000003, 2000004, 2000005]  # New part IDs
loc_ids = [100, 101, 102]  # New location IDs

# Read existing data to find the last time bucket
try:
    fg = fs.get_or_create_feature_group("demand_features_generated", version=1)
    data = fg.read()
    last_bucket = data['time_bucket'].max()
    year = int(str(last_bucket)[:4])
    month = int(str(last_bucket)[4:6])
    start_date = datetime(year, month, 1) + timedelta(days=31)
except:
    start_date = datetime(2014, 1, 1)

# Generate 12 months of new data
time_buckets = []
for i in range(12):
    date = start_date + timedelta(days=31*i)
    date = date.replace(day=1)  # Ensure first day of month
    time_buckets.append(int(date.strftime("%Y%m")))

# Generate demand data
data = []
for sp_id in sp_ids:
    for loc_id in loc_ids:
        # Random base demand and pattern
        base_demand = np.random.randint(50, 500)
        seasonal_amp = np.random.uniform(0.2, 0.4)
        
        for i, bucket in enumerate(time_buckets):
            # Simple seasonal pattern + noise
            seasonal = base_demand * seasonal_amp * np.sin(2 * np.pi * i / 12)
            noise = np.random.normal(0, base_demand * 0.1)
            demand = max(0, int(base_demand + seasonal + noise))
            
            data.append({
                'sp_id': sp_id,
                'loc_id': loc_id,
                'time_bucket': bucket,
                'repetitive_demand_quantity': float(demand)
            })

# Create DataFrame and add lagged features
df = pd.DataFrame(data)
df = df.sort_values(['sp_id', 'loc_id', 'time_bucket'])

df['lagged_1day_demand_quantity'] = df.groupby(['sp_id', 'loc_id'])['repetitive_demand_quantity'].shift(1)
df['lagged_2day_demand_quantity'] = df.groupby(['sp_id', 'loc_id'])['repetitive_demand_quantity'].shift(2)

df = df.dropna()

# Insert into feature store with upsert to handle duplicates
demand_fg = fs.get_or_create_feature_group(
    name="demand_features_generated",
    version=1,
    primary_key=['sp_id', 'loc_id', 'time_bucket'],
    event_time='time_bucket'
)

# Append new data (no upsert needed since we're adding new time periods)
demand_fg.insert(df, write_options={"wait_for_job": False})

print(f"Generated {len(df)} records for {len(sp_ids)} parts x {len(loc_ids)} locations")
print(f"\nSample data:")
print(df.head(10))