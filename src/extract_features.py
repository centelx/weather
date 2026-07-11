import os
import argparse
import pandas as pd
import openmeteo_requests
import requests_cache
from retry_requests import retry
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import time

# Setup the Open-Meteo API client with cache and retry on error
cache_session = requests_cache.CachedSession('.cache', expire_after=3600*24)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=retry_session)

MODELS = ["ecmwf_ifs"]
BASE_VARS = [
    "temperature_2m",
    "relative_humidity_2m",
    "precipitation",
    "cloud_cover",
    "wind_speed_10m"
]

def fetch_single_run(url, lat, lon, run_str, model):
    params = {
        "latitude": lat,
        "longitude": lon,
        "run": run_str,
        "hourly": BASE_VARS,
        "models": model,
        "timezone": "auto"
    }
    
    time.sleep(0.1) # Rate limit protection
    
    try:
        responses = openmeteo.weather_api(url, params=params)
        response = responses[0]
        hourly = response.Hourly()
        
        utc_offset = response.UtcOffsetSeconds()
        start_ts = hourly.Time() + utc_offset
        end_ts = hourly.TimeEnd() + utc_offset
        
        hourly_data = {
            "time": pd.date_range(
                start=pd.to_datetime(start_ts, unit="s", utc=True),
                end=pd.to_datetime(end_ts, unit="s", utc=True),
                freq=pd.Timedelta(seconds=hourly.Interval()),
                inclusive="left"
            )
        }
        
        for i, var_name in enumerate(BASE_VARS):
            hourly_data[var_name] = hourly.Variables(i).ValuesAsNumpy()
            
        df_model_hourly = pd.DataFrame(data=hourly_data)
        # Normalize to local date
        df_model_hourly['Date'] = df_model_hourly['time'].dt.tz_convert(None).dt.date
        return run_str, df_model_hourly
    except Exception as e:
        if "available" not in str(e):
            print(f"Error fetching {run_str}: {e}")
        return run_str, None

def extract_features(city, lat, lon, start_date, end_date, base_path):
    dates = pd.date_range(start=start_date, end=end_date)
    
    print(f"Fetching Single Runs data for {city} from {start_date} to {end_date} (Model: {MODELS[0]})")
    
    url = "https://single-runs-api.open-meteo.com/v1/forecast"
    
    # Collect all unique runs needed for day-1 and day-2 at 00:00 and 12:00
    all_runs = set()
    for t in dates:
        all_runs.add((t - pd.Timedelta(days=1)).strftime("%Y-%m-%dT00:00"))
        all_runs.add((t - pd.Timedelta(days=1)).strftime("%Y-%m-%dT12:00"))
        all_runs.add((t - pd.Timedelta(days=2)).strftime("%Y-%m-%dT00:00"))
        all_runs.add((t - pd.Timedelta(days=2)).strftime("%Y-%m-%dT12:00"))
        
    all_runs = list(all_runs)
    print(f"Total unique API runs to fetch: {len(all_runs)}")
    
    run_data = {}
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {executor.submit(fetch_single_run, url, lat, lon, run_str, MODELS[0]): run_str for run_str in all_runs}
        for future in tqdm(as_completed(futures), total=len(futures), desc="Fetching API runs"):
            run_str, hourly_df = future.result()
            run_data[run_str] = hourly_df
            
    features_list = []
    for t in dates:
        row = {'Date': t.date()}
        
        configs = {
            'day1_0000': (t - pd.Timedelta(days=1)).strftime("%Y-%m-%dT00:00"),
            'day1_1200': (t - pd.Timedelta(days=1)).strftime("%Y-%m-%dT12:00"),
            'day2_0000': (t - pd.Timedelta(days=2)).strftime("%Y-%m-%dT00:00"),
            'day2_1200': (t - pd.Timedelta(days=2)).strftime("%Y-%m-%dT12:00"),
        }
        
        for conf_name, run_str in configs.items():
            hourly_df = run_data.get(run_str)
            if hourly_df is not None and not hourly_df.empty:
                df_target = hourly_df[hourly_df['Date'] == t.date()]
                if not df_target.empty:
                    model_name = MODELS[0]
                    row[f'temperature_2m_max_previous_{conf_name}_{model_name}'] = df_target['temperature_2m'].max()
                    row[f'temperature_2m_min_previous_{conf_name}_{model_name}'] = df_target['temperature_2m'].min()
                    row[f'temperature_2m_mean_previous_{conf_name}_{model_name}'] = df_target['temperature_2m'].mean()
                    row[f'precipitation_sum_previous_{conf_name}_{model_name}'] = df_target['precipitation'].sum()
                    row[f'relative_humidity_2m_mean_previous_{conf_name}_{model_name}'] = df_target['relative_humidity_2m'].mean()
                    row[f'cloud_cover_mean_previous_{conf_name}_{model_name}'] = df_target['cloud_cover'].mean()
                    row[f'wind_speed_10m_max_previous_{conf_name}_{model_name}'] = df_target['wind_speed_10m'].max()
                    
        features_list.append(row)
        
    df_features = pd.DataFrame(features_list)
    
    output_path = os.path.join(base_path, 'data')
    os.makedirs(output_path, exist_ok=True)
    
    out_file = os.path.join(output_path, f"features_{city}.csv")
    df_features.to_csv(out_file, index=False)
    print(f"Success! Features saved to {out_file} with shape {df_features.shape}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--city", required=True)
    parser.add_argument("--lat", required=True, type=float)
    parser.add_argument("--lon", required=True, type=float)
    parser.add_argument("--start", type=str, default="2024-01-01", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", type=str, default="2026-07-15", help="End date (YYYY-MM-DD)")
    args = parser.parse_args()
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    
    extract_features(args.city, args.lat, args.lon, args.start, args.end, project_root)
