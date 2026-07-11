import os
import argparse
import pandas as pd
import numpy as np
import joblib
import json
from scipy.stats import norm

def run_backtest(city, base_path, config, use_fahrenheit=False):
    data_path = os.path.join(base_path, 'data', f"dataset_{city}.csv")
    if not os.path.exists(data_path):
        print(f"Error: Dataset {data_path} not found.")
        return
        
    df = pd.read_csv(data_path)
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values('Date').reset_index(drop=True)
    
    day_of_year = df['Date'].dt.dayofyear
    df['day_of_year_sin'] = np.sin(2 * np.pi * day_of_year / 365.25)
    df['day_of_year_cos'] = np.cos(2 * np.pi * day_of_year / 365.25)
    
    # Dodanie lagowanych cech prawdziwej pogody
    df['Max_Temp_lag2'] = df['Max_Temp'].shift(2)
    df['Avg_Temp_lag2'] = df['Avg_Temp'].shift(2)
    df['Min_Temp_lag2'] = df['Min_Temp'].shift(2)
    df['Max_Temp_lag3'] = df['Max_Temp'].shift(3)
    df['Avg_Temp_lag3'] = df['Avg_Temp'].shift(3)
    df['Min_Temp_lag3'] = df['Min_Temp'].shift(3)
    
    # Amplituda dobowa
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
        
    # Suma opadow z ostatnich 3 dni (oparta na API - bez przesunięcia)
    df[f'precip_sum_3d_{config}'] = df[precip_col].rolling(3).sum()
    
    api_features = [c for c in df.columns if f'_previous_{config}_' in c]
    
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
        
    features = api_features + lag_features + ['day_of_year_sin', 'day_of_year_cos']
    
    if not features:
        print(f"Błąd: Nie znaleziono kolumn cech dla '{config}'.")
        return
        
    df = df.dropna(subset=features, how='all').reset_index(drop=True)
    
    split_idx = int(len(df) * 0.8)
    if split_idx == 0 or split_idx == len(df):
        split_idx = len(df) - min(5, len(df)-1)
        
    df_val = df.iloc[split_idx:].copy()
    
    print(f"Rozpoczynam backtest dla {city.upper()} na zbiorze walidacyjnym ({len(df_val)} dni).")
    print(f"Konfiguracja: {config}")
    
    X_val = df_val[features]
    y_max_true = df_val['Max_Temp'].values
    
    ecmwf_max_col = f"temperature_2m_max_previous_{config}_ecmwf_ifs"
    ecmwf_raw_val = df_val[ecmwf_max_col].values
    
    models_dir = os.path.join(base_path, 'models')
    model_name = f"{city}_model_max_{config}"
    model_path = os.path.join(models_dir, f"{model_name}.pkl")
    
    if not os.path.exists(model_path):
        print(f"Błąd: Model {model_path} nie istnieje. Przetrenuj modele najpierw.")
        return
        
    # Load Hybrid Ensemble
    model = joblib.load(model_path)
    
    # Predict residuals with XGBoost and standard deviation with BayesianRidge
    preds_residual = model['xgb'].predict(X_val)
    _, stds_residual = model['bayes'].predict(X_val, return_std=True)
    
    # Reconstruct absolute predictions
    preds_absolute = ecmwf_raw_val + preds_residual
    
    records = []
    bucket_min, bucket_max = (50, 111) if use_fahrenheit else (15, 46)
    unit_str = "F" if use_fahrenheit else "C"
    
    for i in range(len(df_val)):
        true_temp = y_max_true[i]
        pred_temp = preds_absolute[i]
        std_val = stds_residual[i]
        
        if use_fahrenheit:
            true_temp = true_temp * 1.8 + 32
            pred_temp = pred_temp * 1.8 + 32
            std_val = std_val * 1.8
            
        for b in range(bucket_min, bucket_max):
            prob = norm.cdf(b + 1, loc=pred_temp, scale=std_val) - norm.cdf(b, loc=pred_temp, scale=std_val)
            prob_pct = prob * 100
            
            is_hit = (b <= true_temp < b + 1)
            
            if prob_pct >= 2.0:
                records.append({
                    'predicted_prob': prob_pct,
                    'is_hit': int(is_hit)
                })
                
    if not records:
        print("Brak odpowiednich predykcji powyżej 2% szans w pojedynczych koszykach.")
        return
        
    df_results = pd.DataFrame(records)
    
    bins = [2, 10, 20, 30, 40, 60, 100]
    labels = ['2-10%', '10-20%', '20-30%', '30-40%', '40-60%', '60-100%']
    df_results['prob_bucket'] = pd.cut(df_results['predicted_prob'], bins=bins, labels=labels, right=False)
    
    calibration = df_results.groupby('prob_bucket', observed=True).agg(
        total_predictions=('is_hit', 'count'),
        actual_hits=('is_hit', 'sum'),
        avg_predicted_prob=('predicted_prob', 'mean')
    ).reset_index()
    
    calibration['empirical_win_rate'] = (calibration['actual_hits'] / calibration['total_predictions']) * 100
    
    print("\n" + "="*60)
    print("RAPORT Z KALIBRACJI MODELU (TEST OUT-OF-SAMPLE)")
    print("="*60)
    print(f"Średnie odchylenie standardowe (dynamiczne RMSE): {np.mean(stds_residual):.2f} {unit_str}")
    
    for _, row in calibration.iterrows():
        b = row['prob_bucket']
        total = row['total_predictions']
        if total == 0:
            continue
        avg_pred = row['avg_predicted_prob']
        win_rate = row['empirical_win_rate']
        
        print(f"Kiedy model dawał {b:8s} szans (średnio {avg_pred:4.1f}%):")
        print(f"   Liczba takich zakładów: {total}")
        print(f"   Rzeczywista trafność : {win_rate:4.1f}%")
        diff = win_rate - avg_pred
        print(f"   Odchylenie od modelu  : {diff:+.1f} p.p.")
        print("-" * 60)
        

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--city", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("-f", "--fahrenheit", action="store_true")
    args = parser.parse_args()
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    
    run_backtest(args.city, project_root, args.config, args.fahrenheit)
