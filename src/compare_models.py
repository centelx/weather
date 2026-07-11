import os
import argparse
import pandas as pd
import numpy as np
import joblib
from sklearn.metrics import mean_absolute_error, mean_squared_error

def compare_models(city, base_path, config):
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
    
    all_api_features = [c for c in df.columns if '_previous_' in c]
    df = df.dropna(subset=all_api_features, how='all').reset_index(drop=True)
    
    split_idx = int(len(df) * 0.8)
    if split_idx == 0 or split_idx == len(df):
        split_idx = len(df) - min(5, len(df)-1)
        
    df_val = df.iloc[split_idx:].copy()
    
    print(f"\n--- Porównanie modeli dla: {city.upper()} ({config}) ---")
    print(f"Zbiór walidacyjny: {len(df_val)} dni")
    
    models_dir = os.path.join(base_path, 'models')
    
    for target in ['max', 'min']:
        model_name = f"{city}_model_{target}_{config}"
        model_path = os.path.join(models_dir, f"{model_name}.pkl")
        
        if not os.path.exists(model_path):
            print(f"Pominięto {target.upper()}: model {model_name}.pkl nie istnieje.")
            continue
            
        model = joblib.load(model_path)
        
        y_true = df_val['Max_Temp'].values if target == 'max' else df_val['Min_Temp'].values
        ecmwf_col = f"temperature_2m_{target}_previous_{config}_ecmwf_ifs"
        ecmwf_raw_val = df_val[ecmwf_col].values
        
        preds_residual = model['xgb'].predict(df_val[features])
        preds_absolute = ecmwf_raw_val + preds_residual
        
        # Odrzucenie nan jeśli występują
        valid_idx = ~np.isnan(ecmwf_raw_val) & ~np.isnan(y_true) & ~np.isnan(preds_absolute)
        y_true = y_true[valid_idx]
        ecmwf_raw_val = ecmwf_raw_val[valid_idx]
        preds_absolute = preds_absolute[valid_idx]
        
        if len(y_true) == 0:
            print(f"Brak pełnych danych walidacyjnych dla {target.upper()}.")
            continue
            
        mae_ecmwf = mean_absolute_error(y_true, ecmwf_raw_val)
        rmse_ecmwf = np.sqrt(mean_squared_error(y_true, ecmwf_raw_val))
        
        mae_our = mean_absolute_error(y_true, preds_absolute)
        rmse_our = np.sqrt(mean_squared_error(y_true, preds_absolute))
        
        print(f"\nTarget: {target.upper()} TEMPERATURE")
        print(f"ECMWF (Model Europejski): MAE = {mae_ecmwf:.3f}, RMSE = {rmse_ecmwf:.3f}")
        print(f"Nasz Model (Hybrydowy):   MAE = {mae_our:.3f}, RMSE = {rmse_our:.3f}")
        
        impr_mae = (mae_ecmwf - mae_our) / mae_ecmwf * 100
        impr_rmse = (rmse_ecmwf - rmse_our) / rmse_ecmwf * 100
        print(f"Poprawa MAE:  {impr_mae:+.2f}%")
        print(f"Poprawa RMSE: {impr_rmse:+.2f}%")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--city", required=True)
    parser.add_argument("--config", default="day1_0000")
    args = parser.parse_args()
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    
    compare_models(args.city, project_root, args.config)
