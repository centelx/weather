import os
import argparse
import pandas as pd
import numpy as np
import joblib
from scipy.stats import norm

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
    parser.add_argument("-f", "--fahrenheit", action="store_true")
    parser.add_argument("--std_multiplier", type=float, default=1.0, help="Mnoznik odchylenia (np. 0.75 by zwezic dzwon o 25 proc)")
    parser.add_argument("--algo", type=str, default=None, help="Algorytm (np. svr, lgbm). Jesli podany, laduje z models_opt.")
    args = parser.parse_args()
    
    city = args.city
    use_f = args.fahrenheit
    unit_str = "F" if use_f else "C"
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    
    data_path = os.path.join(project_root, 'data_aws', f"dataset_{city}.csv")
    df = pd.read_csv(data_path)
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values('Date').reset_index(drop=True)
    
    # Feature engineering as in train_aws.py
    day_of_year = df['Date'].dt.dayofyear
    df['day_of_year_sin'] = np.sin(2 * np.pi * day_of_year / 365.25)
    df['day_of_year_cos'] = np.cos(2 * np.pi * day_of_year / 365.25)
    
    df['Max_Temp_lag2'] = df['Max_Temp'].shift(2)
    df['Avg_Temp_lag2'] = df['Avg_Temp'].shift(2)
    df['Min_Temp_lag2'] = df['Min_Temp'].shift(2)
    df['diurnal_range_lag2'] = df['Max_Temp_lag2'] - df['Min_Temp_lag2']
    
    gfs_max_col = "temperature_2m_max_previous_day1_1200_gfs"
    gfs_min_col = "temperature_2m_min_previous_day1_1200_gfs"
    gfs_precip_col = "precipitation_sum_previous_day1_1200_gfs"
    
    hrrr_max_col = "temperature_2m_max_previous_day1_1200_hrrr"
    hrrr_min_col = "temperature_2m_min_previous_day1_1200_hrrr"
    hrrr_precip_col = "precipitation_sum_previous_day1_1200_hrrr"
    
    if gfs_max_col in df.columns and hrrr_max_col in df.columns:
        df['err_max_gfs'] = df['Max_Temp'] - df[gfs_max_col]
        df['err_min_gfs'] = df['Min_Temp'] - df[gfs_min_col]
        df['err_max_hrrr'] = df['Max_Temp'] - df[hrrr_max_col]
        df['err_min_hrrr'] = df['Min_Temp'] - df[hrrr_min_col]
        
        df['err_max_gfs_lag2'] = df['err_max_gfs'].shift(2)
        df['err_min_gfs_lag2'] = df['err_min_gfs'].shift(2)
        df['err_max_hrrr_lag2'] = df['err_max_hrrr'].shift(2)
        df['err_min_hrrr_lag2'] = df['err_min_hrrr'].shift(2)
        
        df['precip_sum_3d_gfs'] = df[gfs_precip_col].rolling(3).sum()
        df['precip_sum_3d_hrrr'] = df[hrrr_precip_col].rolling(3).sum()
        
    api_features = [c for c in df.columns if '_previous_' in c]
    lag_features = [
        'Max_Temp_lag2', 'Avg_Temp_lag2', 'Min_Temp_lag2', 'diurnal_range_lag2',
        'err_max_gfs_lag2', 'err_min_gfs_lag2', 'err_max_hrrr_lag2', 'err_min_hrrr_lag2',
        'precip_sum_3d_gfs', 'precip_sum_3d_hrrr'
    ]
    
    features = api_features + lag_features + ['day_of_year_sin', 'day_of_year_cos', 'Date']
    
    df = df.dropna(subset=features, how='any').reset_index(drop=True)
    
    df['baseline_max'] = (df[gfs_max_col] + df[hrrr_max_col]) / 2.0
    df['baseline_min'] = (df[gfs_min_col] + df[hrrr_min_col]) / 2.0
    
    split_date = pd.to_datetime('2026-04-01')
    df_val = df[df['Date'] >= split_date].copy()
    X_val = df_val[features].drop(columns=['Date'])
    
    if args.algo:
        models_dir = os.path.join(project_root, 'models_opt')
        suffix = f"_{args.algo}"
    else:
        models_dir = os.path.join(project_root, 'models_aws')
        suffix = ""
        
    model_max = joblib.load(os.path.join(models_dir, f"{city}_model_max_aws{suffix}.pkl"))
    model_min = joblib.load(os.path.join(models_dir, f"{city}_model_min_aws{suffix}.pkl"))
    
    X_val_max = df_val[model_max['features']] if 'features' in model_max else X_val
    X_val_min = df_val[model_min['features']] if 'features' in model_min else X_val
    
    resid_max = model_max['xgb'].predict(X_val_max)
    _, std_max = model_max['bayes'].predict(X_val_max, return_std=True)
    preds_max = df_val['baseline_max'].values + resid_max
    
    resid_min = model_min['xgb'].predict(X_val_min)
    _, std_min = model_min['bayes'].predict(X_val_min, return_std=True)
    preds_min = df_val['baseline_min'].values + resid_min
    
    if use_f:
        preds_max = preds_max * 1.8 + 32
        preds_min = preds_min * 1.8 + 32
        std_max = std_max * 1.8
        std_min = std_min * 1.8
        
    std_max = std_max * args.std_multiplier
    std_min = std_min * args.std_multiplier
        
    df_val['Pred_Max'] = preds_max
    df_val['Std_Max'] = std_max
    df_val['Pred_Min'] = preds_min
    df_val['Std_Min'] = std_min
    
    # Przewidywania zakończone, tniemy do horyzontu (np. lipiec)
    df_val = df_val[df_val['Date'] <= '2026-07-08']
    df_val = df_val.sort_values('Date', ascending=False)
    
    csv_records = []
    for _, row in df_val.iterrows():
        target_date = row['Date'].strftime('%Y-%m-%d')
        
        for type_label, prefix in [("MAX", "Max"), ("MIN", "Min")]:
            pred = row[f'Pred_{prefix}']
            std = row[f'Std_{prefix}']
            buckets = get_raw_buckets(pred, std, unit_str)
            
            for b_range, prob in buckets:
                csv_records.append({
                    'target_date': target_date,
                    'forecast_horizon': 'aws_day1_1200',
                    'type': type_label,
                    'bucket': b_range,
                    'model_probability': round(prob, 4)
                })
                
    out_path_csv = os.path.join(project_root, f'predictions_history_{city}_aws.csv')
    df_csv = pd.DataFrame(csv_records)
    df_csv.to_csv(out_path_csv, index=False)
    
    print(f"Pomyślnie wygenerowano plik z predykcjami do symulacji giełdy: {out_path_csv}")

if __name__ == "__main__":
    run()
