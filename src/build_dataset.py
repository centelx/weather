import os
import argparse
import pandas as pd

def build_dataset(city, base_path, y_dir="y_data_f"):
    # Path to y_data (targets)
    city_path = os.path.join(base_path, y_dir, city)
    merged_csv_path = os.path.join(city_path, f"merged_{city}.csv")
    
    # Path to features
    features_csv_path = os.path.join(base_path, 'data', f"features_{city}.csv")
    
    if not os.path.exists(merged_csv_path):
        print(f"Error: Could not find target file at {merged_csv_path}")
        return
        
    if not os.path.exists(features_csv_path):
        print(f"Error: Could not find features file at {features_csv_path}. Please run extract_features.py first.")
        return
        
    df_y = pd.read_csv(merged_csv_path)
    df_y['Date'] = pd.to_datetime(df_y['Date']).dt.date
    
    df_features = pd.read_csv(features_csv_path)
    df_features['Date'] = pd.to_datetime(df_features['Date']).dt.date
    
    # Merge
    final_df = pd.merge(df_y, df_features, on='Date', how='left')
    
    # Drop rows without features (if any target date wasn't inside features date range)
    # We can check how many were dropped
    initial_len = len(final_df)
    final_df = final_df.dropna(subset=[col for col in final_df.columns if col not in df_y.columns])
    dropped = initial_len - len(final_df)
    if dropped > 0:
        print(f"Warning: Dropped {dropped} rows due to missing features. Check date ranges.")
        
    # Save
    out_file = os.path.join(base_path, 'data', f"dataset_{city}.csv")
    final_df.to_csv(out_file, index=False)
    print(f"Success! Dataset merged and saved to {out_file} with shape {final_df.shape}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--city", required=True)
    parser.add_argument("--y_dir", type=str, default="y_data_f", help="Directory for y_data")
    args = parser.parse_args()
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    
    build_dataset(args.city, project_root, y_dir=args.y_dir)
