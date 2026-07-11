import os
import argparse
import pandas as pd
import numpy as np
import joblib
from scipy.stats import norm

def get_predictions(city, base_path, config, use_fahrenheit):
    data_path = os.path.join(base_path, 'data', f"dataset_{city}.csv")
    df = pd.read_csv(data_path)
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values('Date').reset_index(drop=True)
    
    day_of_year = df['Date'].dt.dayofyear
    df['day_of_year_sin'] = np.sin(2 * np.pi * day_of_year / 365.25)
    df['day_of_year_cos'] = np.cos(2 * np.pi * day_of_year / 365.25)
    
    df['Max_Temp_lag2'] = df['Max_Temp'].shift(2)
    df['Avg_Temp_lag2'] = df['Avg_Temp'].shift(2)
    df['Min_Temp_lag2'] = df['Min_Temp'].shift(2)
    df['Max_Temp_lag3'] = df['Max_Temp'].shift(3)
    df['Avg_Temp_lag3'] = df['Avg_Temp'].shift(3)
    df['Min_Temp_lag3'] = df['Min_Temp'].shift(3)
    df['diurnal_range_lag2'] = df['Max_Temp_lag2'] - df['Min_Temp_lag2']
    df['diurnal_range_lag3'] = df['Max_Temp_lag3'] - df['Min_Temp_lag3']

    max_col = f"temperature_2m_max_previous_{config}_ecmwf_ifs"
    min_col = f"temperature_2m_min_previous_{config}_ecmwf_ifs"
    precip_col = f"precipitation_sum_previous_{config}_ecmwf_ifs"
    
    if max_col in df.columns:
        df[f'err_max_{config}'] = df['Max_Temp'] - df[max_col]
        df[f'err_min_{config}'] = df['Min_Temp'] - df[min_col]
        
        df[f'err_max_{config}_lag2'] = df[f'err_max_{config}'].shift(2)
        df[f'err_min_{config}_lag2'] = df[f'err_min_{config}'].shift(2)
        df[f'err_max_{config}_lag3'] = df[f'err_max_{config}'].shift(3)
        df[f'err_min_{config}_lag3'] = df[f'err_min_{config}'].shift(3)
        
        df[f'precip_sum_3d_{config}'] = df[precip_col].rolling(3).sum()

    if "day1" in config:
        lag_features = [
            'Max_Temp_lag2', 'Avg_Temp_lag2', 'Min_Temp_lag2', 'diurnal_range_lag2',
            f'err_max_{config}_lag2', f'err_min_{config}_lag2',
            f'precip_sum_3d_{config}'
        ]
    else:
        lag_features = [
            'Max_Temp_lag3', 'Avg_Temp_lag3', 'Min_Temp_lag3', 'diurnal_range_lag3',
            f'err_max_{config}_lag3', f'err_min_{config}_lag3',
            f'precip_sum_3d_{config}'
        ]

    features = [c for c in df.columns if f'_previous_{config}_' in c] + lag_features + ['day_of_year_sin', 'day_of_year_cos']
        
    df = df.dropna(subset=features, how='all').reset_index(drop=True)
    
    split_date = pd.to_datetime('2026-06-01')
    df_val = df[df['Date'] >= split_date].copy()
    
    X_val = df_val[features]
    
    models_dir = os.path.join(base_path, 'models')
    model_max = joblib.load(os.path.join(models_dir, f"{city}_model_max_{config}.pkl"))
    model_min = joblib.load(os.path.join(models_dir, f"{city}_model_min_{config}.pkl"))
    
    ecmwf_max_raw = df_val[max_col].values
    ecmwf_min_raw = df_val[min_col].values
    
    resid_max = model_max['xgb'].predict(X_val)
    _, std_max = model_max['bayes'].predict(X_val, return_std=True)
    preds_max = ecmwf_max_raw + resid_max
    
    resid_min = model_min['xgb'].predict(X_val)
    _, std_min = model_min['bayes'].predict(X_val, return_std=True)
    preds_min = ecmwf_min_raw + resid_min
    
    if use_fahrenheit:
        preds_max = preds_max * 1.8 + 32
        preds_min = preds_min * 1.8 + 32
        std_max = std_max * 1.8
        std_min = std_min * 1.8
    
    df_val[f'Pred_Max'] = preds_max
    df_val[f'Std_Max'] = std_max
    df_val[f'Pred_Min'] = preds_min
    df_val[f'Std_Min'] = std_min
    
    return df_val[['Date', 'Pred_Max', 'Std_Max', 'Pred_Min', 'Std_Min']]

def get_raw_buckets(pred, std_val, unit):
    if np.isnan(pred) or np.isnan(std_val):
        return []
    
    res = []
    if unit == 'F':
        center_even = int(np.round(pred)) // 2 * 2
        buckets = [center_even - 2, center_even, center_even + 2]
        for b in buckets:
            prob = norm.cdf(b + 1.5, loc=pred, scale=std_val) - norm.cdf(b - 0.5, loc=pred, scale=std_val)
            res.append((f"{b}-{b+1}", prob))
    else:
        center = int(np.round(pred))
        buckets = [center - 1, center, center + 1]
        for b in buckets:
            prob = norm.cdf(b + 0.5, loc=pred, scale=std_val) - norm.cdf(b - 0.5, loc=pred, scale=std_val)
            res.append((f"{b}-{b+1}", prob))
            
    return res

def run():
    parser = argparse.ArgumentParser()
    parser.add_argument("--city", default="miami")
    args = parser.parse_args()
    
    city = args.city
    US_CITIES = ['houston', 'dallas', 'chicago', 'sanfrancisco', 'miami', 'lasvegas', 'newyork', 'nyc', 'losangeles', 'denver']
    use_f = city.lower() in US_CITIES
    unit_str = "F" if use_f else "C"
    
    base_path = r'C:\Users\barto\Desktop\polymarket\weather'
    
    # Przewidujemy Day 2 Ahead dla runów 0000 i 1200
    df_0000 = get_predictions(city, base_path, 'day2_0000', use_f)
    df_1200 = get_predictions(city, base_path, 'day2_1200', use_f)
    
    df_merged = pd.merge(df_0000, df_1200, on='Date', suffixes=('_0000', '_1200'))
    df_merged = df_merged[df_merged['Date'] <= '2026-07-08']
    df_merged = df_merged.sort_values('Date', ascending=False)
    
    csv_records = []
    
    for _, row in df_merged.iterrows():
        target_date = row['Date'].strftime('%Y-%m-%d')
        
        for type_label, prefix in [("MAX", "Max"), ("MIN", "Min")]:
            
            # Pobierzmy koszyki dla obu runów
            pred_0000 = row[f'Pred_{prefix}_0000']
            std_0000 = row[f'Std_{prefix}_0000']
            buckets_0000 = get_raw_buckets(pred_0000, std_0000, unit_str)
            
            pred_1200 = row[f'Pred_{prefix}_1200']
            std_1200 = row[f'Std_{prefix}_1200']
            buckets_1200 = get_raw_buckets(pred_1200, std_1200, unit_str)
            
            # Scal koszyki (zbierzmy wszystkie unikalne klucze)
            all_buckets = set([b[0] for b in buckets_0000] + [b[0] for b in buckets_1200])
            
            for b_range in all_buckets:
                prob_0000 = next((p for b, p in buckets_0000 if b == b_range), 0.0)
                prob_1200 = next((p for b, p in buckets_1200 if b == b_range), 0.0)
                
                csv_records.append({
                    'target_date': target_date,
                    'type': type_label,
                    'bucket': b_range,
                    'model_probability_0000': round(prob_0000, 4),
                    'model_probability_1200': round(prob_1200, 4)
                })

    data_dir = os.path.join(base_path, 'data', 'predictions_intraday')
    os.makedirs(data_dir, exist_ok=True)
    out_path_csv = os.path.join(data_dir, f'predictions_intraday_day2_{city}.csv')
    df_csv = pd.DataFrame(csv_records)
    df_csv.to_csv(out_path_csv, index=False)
        
    print(f"Pomyślnie wygenerowano plik: {out_path_csv}")

if __name__ == "__main__":
    run()
