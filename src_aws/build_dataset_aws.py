import os
import argparse
import pandas as pd

def build_dataset(city, base_path):
    # Path to y_data (targets)
    city_path = os.path.join(base_path, 'y_data_aws')
    merged_csv_path = os.path.join(city_path, f"y_{city}.csv")
    
    # Check if target exists
    if not os.path.exists(merged_csv_path):
        print(f"Error: Could not find target file at {merged_csv_path}")
        return

    # Check for features file (with and without 'precise')
    features_dir = os.path.join(base_path, 'aws_datasets')
    
    gfs_path_precise = os.path.join(features_dir, f"features_{city}_precise_gfs_full.csv")
    gfs_path_normal = os.path.join(features_dir, f"features_{city}_gfs_full.csv")
    
    hrrr_path_precise = os.path.join(features_dir, f"features_{city}_precise_hrrr_full.csv")
    hrrr_path_normal = os.path.join(features_dir, f"features_{city}_hrrr_full.csv")
    
    gfs_path = gfs_path_precise if os.path.exists(gfs_path_precise) else gfs_path_normal
    hrrr_path = hrrr_path_precise if os.path.exists(hrrr_path_precise) else hrrr_path_normal

    if not os.path.exists(gfs_path) or not os.path.exists(hrrr_path):
        print(f"Error: Could not find features files for GFS or HRRR in {features_dir}")
        return

    # Read targets and adapt columns to old format
    df_y = pd.read_csv(merged_csv_path)
    # y_data_aws has columns: date,temperature_max,temperature_min,temperature_mean
    # Targets are in Fahrenheit, convert them to Celsius so it matches GFS/HRRR features
    df_y = df_y.rename(columns={
        'date': 'Date',
        'temperature_max': 'Max_Temp',
        'temperature_min': 'Min_Temp',
        'temperature_mean': 'Avg_Temp'
    })
    df_y['Max_Temp'] = (df_y['Max_Temp'] - 32) / 1.8
    df_y['Min_Temp'] = (df_y['Min_Temp'] - 32) / 1.8
    df_y['Avg_Temp'] = (df_y['Avg_Temp'] - 32) / 1.8
    
    df_y['Date'] = pd.to_datetime(df_y['Date']).dt.date
    
    # Read features
    df_gfs = pd.read_csv(gfs_path)
    df_gfs['Date'] = pd.to_datetime(df_gfs['Date']).dt.date
    
    df_hrrr = pd.read_csv(hrrr_path)
    df_hrrr['Date'] = pd.to_datetime(df_hrrr['Date']).dt.date
    
    # Merge targets with GFS
    final_df = pd.merge(df_y, df_gfs, on='Date', how='left')
    # Merge with HRRR
    final_df = pd.merge(final_df, df_hrrr, on='Date', how='left')
    
    # Drop rows without features
    initial_len = len(final_df)
    # We drop NA if ANY of the feature columns are missing.
    feature_cols = [col for col in final_df.columns if col not in df_y.columns]
    final_df = final_df.dropna(subset=feature_cols)
    
    dropped = initial_len - len(final_df)
    if dropped > 0:
        print(f"Warning: Dropped {dropped} rows due to missing features. Check date ranges.")
        
    # Save
    out_dir = os.path.join(base_path, 'data_aws')
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, f"dataset_{city}.csv")
    final_df.to_csv(out_file, index=False)
    print(f"Success! Dataset merged and saved to {out_file} with shape {final_df.shape}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--city", required=True)
    args = parser.parse_args()
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    
    build_dataset(args.city, project_root)
