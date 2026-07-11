import os
import argparse
import pandas as pd
import openmeteo_requests
import requests_cache
from retry_requests import retry
import joblib
from datetime import datetime, timedelta, timezone
import numpy as np
from scipy.stats import norm

cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=retry_session)

MODEL_NAME = "ecmwf_ifs"
BASE_VARS = [
    "temperature_2m",
    "relative_humidity_2m",
    "precipitation",
    "cloud_cover",
    "wind_speed_10m"
]

def fetch_run(lat, lon, run_str):
    url = "https://single-runs-api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "run": run_str,
        "hourly": BASE_VARS,
        "models": MODEL_NAME,
        "timezone": "auto"
    }
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
        df_model_hourly['Date'] = df_model_hourly['time'].dt.tz_convert(None).dt.date
        return df_model_hourly
    except Exception as e:
        print(f"Error fetching run {run_str}: {e}")
        return None

def predict_temperature(city, lat, lon, base_path, run_hour, use_fahrenheit=False):
    models_dir = os.path.join(base_path, 'models')
    
    required_models = [
        f"{city}_model_max_day1_{run_hour}.pkl", f"{city}_model_min_day1_{run_hour}.pkl",
        f"{city}_model_max_day2_{run_hour}.pkl", f"{city}_model_min_day2_{run_hour}.pkl"
    ]
    for rm in required_models:
        if not os.path.exists(os.path.join(models_dir, rm)):
            print(f"Error: Model {rm} not found. Upewnij się, że modele (BayesianRidge) są wytrenowane.")
            return
            
    print(f"Pobieranie najnowszych prognoz dla {city.upper()} (Uruchomienie: {run_hour} UTC)...")
    
    today = datetime.now(timezone.utc).date()
    tomorrow = today + timedelta(days=1)
    day_after = today + timedelta(days=2)
    
    run_str_day1 = f"{today.strftime('%Y-%m-%d')}T{run_hour[:2]}:{run_hour[2:]}"
    
    df_run = fetch_run(lat, lon, run_str_day1)
    if df_run is None or df_run.empty:
        print(f"Błąd: Nie udało się pobrać runu {run_str_day1}.")
        return
        
    agg_dict = {
        'temperature_2m': ['max', 'min'],
        'precipitation': ['sum'],
        'relative_humidity_2m': ['mean'],
        'cloud_cover': ['mean'],
        'wind_speed_10m': ['max']
    }
    
    df_daily = df_run.groupby('Date').agg(agg_dict)
    
    if tomorrow not in df_daily.index or day_after not in df_daily.index:
        print("Błąd: Pobrany run nie zawiera prognoz dla jutra/pojutrza.")
        return
        
    row_day1 = df_daily.loc[[tomorrow]].copy()
    row_day2 = df_daily.loc[[day_after]].copy()
    
    new_cols_day1 = []
    new_cols_day2 = []
    for col_name, agg_func in df_daily.columns:
        new_cols_day1.append(f"{col_name}_{agg_func}_previous_day1_{run_hour}_{MODEL_NAME}")
        new_cols_day2.append(f"{col_name}_{agg_func}_previous_day2_{run_hour}_{MODEL_NAME}")
        
    row_day1.columns = new_cols_day1
    row_day2.columns = new_cols_day2
    row_day1 = row_day1.reset_index()
    row_day2 = row_day2.reset_index()
    
    df_day1 = pd.DataFrame({'Date': [tomorrow]})
    df_day2 = pd.DataFrame({'Date': [day_after]})
    df_day1 = pd.merge(df_day1, row_day1, on='Date', how='left')
    df_day2 = pd.merge(df_day2, row_day2, on='Date', how='left')
    
    # Feature Engineering: Day of Year
    df_day1['day_of_year_sin'] = np.sin(2 * np.pi * pd.to_datetime(df_day1['Date']).dt.dayofyear / 365.25)
    df_day1['day_of_year_cos'] = np.cos(2 * np.pi * pd.to_datetime(df_day1['Date']).dt.dayofyear / 365.25)
    df_day2['day_of_year_sin'] = np.sin(2 * np.pi * pd.to_datetime(df_day2['Date']).dt.dayofyear / 365.25)
    df_day2['day_of_year_cos'] = np.cos(2 * np.pi * pd.to_datetime(df_day2['Date']).dt.dayofyear / 365.25)
    
    # Load historical data for lags
    data_path = os.path.join(base_path, 'data', f"dataset_{city}.csv")
    if not os.path.exists(data_path):
        print(f"Error: {data_path} not found. Brak danych historycznych do opóźnień!")
        return
    df_hist = pd.read_csv(data_path)
    df_hist['Date'] = pd.to_datetime(df_hist['Date']).dt.date
    
    today = datetime.now(timezone.utc).date()
    yesterday = today - timedelta(days=1)
    
    row_today = df_hist[df_hist['Date'] == today]
    row_yesterday = df_hist[df_hist['Date'] == yesterday]
    
    if row_today.empty or row_yesterday.empty:
        print(f"WARNING: Brak pełnych danych dla dzisiaj ({today}) lub wczoraj ({yesterday}) w {data_path}!")
        print("Model użyje wartości zastępczych (średnich), co drastycznie obniży dokładność.")
        # Wypełniamy zerami/nanami, imputer sobie poradzi (choć zepsuje wynik)
        max_lag1, avg_lag1, min_lag1 = np.nan, np.nan, np.nan
        max_lag2, avg_lag2, min_lag2 = np.nan, np.nan, np.nan
        err_max_lag1, err_min_lag1, err_max_lag2, err_min_lag2 = np.nan, np.nan, np.nan, np.nan
        precip_sum_3d_day1, precip_sum_3d_day2 = np.nan, np.nan
    else:
        max_lag1 = row_today['Max_Temp'].values[0]
        avg_lag1 = row_today['Avg_Temp'].values[0]
        min_lag1 = row_today['Min_Temp'].values[0]
        max_lag2 = row_yesterday['Max_Temp'].values[0]
        avg_lag2 = row_yesterday['Avg_Temp'].values[0]
        min_lag2 = row_yesterday['Min_Temp'].values[0]
        
        # Błędy ecmwf dla day1
        ecmwf_max_d1_col = f"temperature_2m_max_previous_day1_{run_hour}_ecmwf_ifs"
        ecmwf_min_d1_col = f"temperature_2m_min_previous_day1_{run_hour}_ecmwf_ifs"
        if ecmwf_max_d1_col in row_today.columns:
            err_max_lag1 = max_lag1 - row_today[ecmwf_max_d1_col].values[0]
            err_min_lag1 = min_lag1 - row_today[ecmwf_min_d1_col].values[0]
            err_max_lag2 = max_lag2 - row_yesterday[ecmwf_max_d1_col].values[0]
            err_min_lag2 = min_lag2 - row_yesterday[ecmwf_min_d1_col].values[0]
            
            # Opady
            precip_col = f"precipitation_sum_previous_day1_{run_hour}_ecmwf_ifs"
            day_before = yesterday - timedelta(days=1)
            row_db = df_hist[df_hist['Date'] == day_before]
            val1 = row_today[precip_col].values[0]
            val2 = row_yesterday[precip_col].values[0]
            val3 = row_db[precip_col].values[0] if not row_db.empty else 0
            precip_sum_3d_day1 = val1 + val2 + val3
        else:
            err_max_lag1, err_min_lag1, err_max_lag2, err_min_lag2 = np.nan, np.nan, np.nan, np.nan
            precip_sum_3d_day1 = np.nan
            
    df_day1['Max_Temp_lag1'] = max_lag1
    df_day1['Avg_Temp_lag1'] = avg_lag1
    df_day1['Min_Temp_lag1'] = min_lag1
    df_day1['Max_Temp_lag2'] = max_lag2
    df_day1['Avg_Temp_lag2'] = avg_lag2
    df_day1['Min_Temp_lag2'] = min_lag2
    df_day1['diurnal_range_lag1'] = max_lag1 - min_lag1
    df_day1[f'err_max_day1_{run_hour}_lag1'] = err_max_lag1
    df_day1[f'err_min_day1_{run_hour}_lag1'] = err_min_lag1
    df_day1[f'err_max_day1_{run_hour}_lag2'] = err_max_lag2
    df_day1[f'err_min_day1_{run_hour}_lag2'] = err_min_lag2
    df_day1[f'precip_sum_3d_day1_{run_hour}'] = precip_sum_3d_day1
    
    # Dla day2 stosujemy uproszczenie (używamy tych samych opóźnień co day1, 
    # ponieważ day2 nie ma dostępu do "prawdziwej" jutrzejszej pogody)
    df_day2['Max_Temp_lag1'] = max_lag1
    df_day2['Avg_Temp_lag1'] = avg_lag1
    df_day2['Min_Temp_lag1'] = min_lag1
    df_day2['Max_Temp_lag2'] = max_lag2
    df_day2['Avg_Temp_lag2'] = avg_lag2
    df_day2['Min_Temp_lag2'] = min_lag2
    df_day2['diurnal_range_lag1'] = max_lag1 - min_lag1
    df_day2[f'err_max_day2_{run_hour}_lag1'] = err_max_lag1
    df_day2[f'err_min_day2_{run_hour}_lag1'] = err_min_lag1
    df_day2[f'err_max_day2_{run_hour}_lag2'] = err_max_lag2
    df_day2[f'err_min_day2_{run_hour}_lag2'] = err_min_lag2
    df_day2[f'precip_sum_3d_day2_{run_hour}'] = precip_sum_3d_day1
    
    base_lag_cols = ['Max_Temp_lag1', 'Avg_Temp_lag1', 'Min_Temp_lag1', 'Max_Temp_lag2', 'Avg_Temp_lag2', 'Min_Temp_lag2', 'diurnal_range_lag1']
    
    # Load Models (Pipelines)
    model_max_d1 = joblib.load(os.path.join(models_dir, f"{city}_model_max_day1_{run_hour}.pkl"))
    model_min_d1 = joblib.load(os.path.join(models_dir, f"{city}_model_min_day1_{run_hour}.pkl"))
    model_max_d2 = joblib.load(os.path.join(models_dir, f"{city}_model_max_day2_{run_hour}.pkl"))
    model_min_d2 = joblib.load(os.path.join(models_dir, f"{city}_model_min_day2_{run_hour}.pkl"))
    
    features_day1 = [c for c in df_day1.columns if f'_previous_day1_{run_hour}_' in c] + base_lag_cols + [
        f'err_max_day1_{run_hour}_lag1', f'err_min_day1_{run_hour}_lag1',
        f'err_max_day1_{run_hour}_lag2', f'err_min_day1_{run_hour}_lag2',
        f'precip_sum_3d_day1_{run_hour}', 'day_of_year_sin', 'day_of_year_cos'
    ]
    
    features_day2 = [c for c in df_day2.columns if f'_previous_day2_{run_hour}_' in c] + base_lag_cols + [
        f'err_max_day2_{run_hour}_lag1', f'err_min_day2_{run_hour}_lag1',
        f'err_max_day2_{run_hour}_lag2', f'err_min_day2_{run_hour}_lag2',
        f'precip_sum_3d_day2_{run_hour}', 'day_of_year_sin', 'day_of_year_cos'
    ]
    
    # Zabezpieczenie przed brakiem kolumn
    for f in features_day1:
        if f not in df_day1.columns: df_day1[f] = np.nan
    for f in features_day2:
        if f not in df_day2.columns: df_day2[f] = np.nan
        
    X_d1 = df_day1[features_day1]
    X_d2 = df_day2[features_day2]
    
    # ECMWF raw absolute values
    ecmwf_max_d1_col = f"temperature_2m_max_previous_day1_{run_hour}_ecmwf_ifs"
    ecmwf_min_d1_col = f"temperature_2m_min_previous_day1_{run_hour}_ecmwf_ifs"
    ecmwf_max_d2_col = f"temperature_2m_max_previous_day2_{run_hour}_ecmwf_ifs"
    ecmwf_min_d2_col = f"temperature_2m_min_previous_day2_{run_hour}_ecmwf_ifs"
    
    ecmwf_max_d1 = float(df_day1[ecmwf_max_d1_col].iloc[0])
    ecmwf_min_d1 = float(df_day1[ecmwf_min_d1_col].iloc[0])
    ecmwf_max_d2 = float(df_day2[ecmwf_max_d2_col].iloc[0])
    ecmwf_min_d2 = float(df_day2[ecmwf_min_d2_col].iloc[0])
    
    # Predict residual and dynamic std using Hybrid Ensemble
    resid_max_d1 = model_max_d1['xgb'].predict(X_d1)
    _, std_max_d1 = model_max_d1['bayes'].predict(X_d1, return_std=True)
    
    resid_min_d1 = model_min_d1['xgb'].predict(X_d1)
    _, std_min_d1 = model_min_d1['bayes'].predict(X_d1, return_std=True)
    
    resid_max_d2 = model_max_d2['xgb'].predict(X_d2)
    _, std_max_d2 = model_max_d2['bayes'].predict(X_d2, return_std=True)
    
    resid_min_d2 = model_min_d2['xgb'].predict(X_d2)
    _, std_min_d2 = model_min_d2['bayes'].predict(X_d2, return_std=True)
    
    # Reconstruct absolute predictions
    pred_max_d1 = ecmwf_max_d1 + float(resid_max_d1[0])
    pred_min_d1 = ecmwf_min_d1 + float(resid_min_d1[0])
    pred_max_d2 = ecmwf_max_d2 + float(resid_max_d2[0])
    pred_min_d2 = ecmwf_min_d2 + float(resid_min_d2[0])
    
    std_max_d1 = float(std_max_d1[0])
    std_min_d1 = float(std_min_d1[0])
    std_max_d2 = float(std_max_d2[0])
    std_min_d2 = float(std_min_d2[0])

    unit_str = "C"
    if use_fahrenheit:
        pred_max_d1 = pred_max_d1 * 1.8 + 32
        pred_min_d1 = pred_min_d1 * 1.8 + 32
        pred_max_d2 = pred_max_d2 * 1.8 + 32
        pred_min_d2 = pred_min_d2 * 1.8 + 32
        
        std_max_d1 *= 1.8
        std_min_d1 *= 1.8
        std_max_d2 *= 1.8
        std_min_d2 *= 1.8
        
        unit_str = "F"

    def print_probs(pred, std_val, unit):
        print(f"   (Dynamiczne odchylenie std: {std_val:.2f} {unit})")
        center_bucket = int(np.floor(pred))
        buckets = [center_bucket - 2, center_bucket - 1, center_bucket, center_bucket + 1, center_bucket + 2]
        
        print("   Szanse procentowe w koszykach (co 1 stopien):")
        for b in buckets:
            prob = norm.cdf(b + 1, loc=pred, scale=std_val) - norm.cdf(b, loc=pred, scale=std_val)
            prob_pct = prob * 100
            if prob_pct > 0.5:
                star = " *" if b == center_bucket else ""
                print(f"     [{b:3d} {unit} - {b}.99 {unit}] : {prob_pct:4.1f}% {star}")
    
    print("\n" + "="*60)
    print(f"POLYMARKET PREDICTIONS FOR {city.upper()} (RUN: {run_hour} UTC)")
    print("="*60)
    
    print(f"DAY 1 (Jutro, {tomorrow}):")
    print(f"   MAX Temp: {pred_max_d1:.1f} {unit_str}")
    print_probs(pred_max_d1, std_max_d1, unit_str)
    print(f"   MIN Temp: {pred_min_d1:.1f} {unit_str}")
    print_probs(pred_min_d1, std_min_d1, unit_str)
    print("-" * 60)
    
    print(f"DAY 2 (Pojutrze, {day_after}):")
    print(f"   MAX Temp: {pred_max_d2:.1f} {unit_str}")
    print_probs(pred_max_d2, std_max_d2, unit_str)
    print(f"   MIN Temp: {pred_min_d2:.1f} {unit_str}")
    print_probs(pred_min_d2, std_min_d2, unit_str)
    print("="*60 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--city", required=True)
    parser.add_argument("--lat", required=True, type=float)
    parser.add_argument("--lon", required=True, type=float)
    parser.add_argument("--run_hour", required=True, choices=["0000", "1200"])
    parser.add_argument("-f", "--fahrenheit", action="store_true")
    args = parser.parse_args()
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    
    predict_temperature(args.city, args.lat, args.lon, project_root, args.run_hour, args.fahrenheit)
