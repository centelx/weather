import os
import argparse
import pandas as pd
import numpy as np
from sklearn.linear_model import BayesianRidge
import xgboost as xgb
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.model_selection import TimeSeriesSplit, RandomizedSearchCV
import joblib
import json

def train_model(X, y_residual, y_true_absolute, ecmwf_absolute, model_name, output_dir):
    # Sort by index just in case
    X = X.sort_index()
    y_residual = y_residual.sort_index()
    y_true_absolute = y_true_absolute.sort_index()
    ecmwf_absolute = ecmwf_absolute.sort_index()
    
    # Chronological split: Hard Date Split to prevent data leakage
    # X['Date'] must be included in X when passed to this function
    split_date = pd.to_datetime('2026-06-01')
    
    train_mask = X['Date'] < split_date
    val_mask = X['Date'] >= split_date
    
    X_train = X[train_mask].drop(columns=['Date'])
    X_val = X[val_mask].drop(columns=['Date'])
    y_train, y_val = y_residual[train_mask], y_residual[val_mask]
    y_true_val = y_true_absolute[val_mask]
    ecmwf_val = ecmwf_absolute[val_mask]
    
    print(f"\n--- Training {model_name} (Hybrid Ensemble: XGBoost + BayesianRidge) ---")
    print(f"Train size: {len(X_train)}, Val size: {len(X_val)}")
    
    xgb_pipeline = Pipeline([
        ('imputer', SimpleImputer(strategy='mean')),
        ('scaler', StandardScaler()),
        ('regressor', xgb.XGBRegressor(random_state=42))
    ])
    
    bayes_pipeline = Pipeline([
        ('imputer', SimpleImputer(strategy='mean')),
        ('scaler', StandardScaler()),
        ('regressor', BayesianRidge(compute_score=True))
    ])
    
    # Bezpieczna optymalizacja hiperparametrów (TimeSeriesSplit zapobiega wyciekom z przyszłości)
    tscv = TimeSeriesSplit(n_splits=3)
    
    xgb_param_dist = {
        'regressor__max_depth': [2, 3, 4],
        'regressor__learning_rate': [0.01, 0.05, 0.1],
        'regressor__n_estimators': [50, 100, 150]
    }
    
    bayes_param_dist = {
        'regressor__alpha_1': [1e-6, 1e-5, 1e-4, 1e-3],
        'regressor__lambda_1': [1e-6, 1e-5, 1e-4, 1e-3]
    }
    
    # Optymalizacja XGBoost
    xgb_search = RandomizedSearchCV(
        xgb_pipeline, param_distributions=xgb_param_dist,
        n_iter=10, cv=tscv, scoring='neg_mean_absolute_error',
        random_state=42, n_jobs=1
    )
    xgb_search.fit(X_train, y_train)
    best_xgb = xgb_search.best_estimator_
    
    # Optymalizacja BayesianRidge
    bayes_search = RandomizedSearchCV(
        bayes_pipeline, param_distributions=bayes_param_dist,
        n_iter=10, cv=tscv, scoring='neg_mean_absolute_error',
        random_state=42, n_jobs=1
    )
    bayes_search.fit(X_train, y_train)
    best_bayes = bayes_search.best_estimator_
    
    print(f"XGBoost best params: {xgb_search.best_params_}")
    print(f"Bayes best params: {bayes_search.best_params_}")
    
    preds_residual = best_xgb.predict(X_val)
    _, stds = best_bayes.predict(X_val, return_std=True)
    
    # Reconstruct absolute predictions
    preds_absolute = ecmwf_val.values + preds_residual
    
    mae = mean_absolute_error(y_true_val, preds_absolute)
    rmse = np.sqrt(mean_squared_error(y_true_val, preds_absolute))
    
    print(f"Validation Absolute MAE: {mae:.2f}")
    print(f"Validation Absolute RMSE: {rmse:.2f}")
    print(f"Average Model Confidence (Dynamic RMSE/STD): {np.mean(stds):.2f}")
    
    # Save the model
    os.makedirs(output_dir, exist_ok=True)
    model_path = os.path.join(output_dir, f"{model_name}.pkl")
    hybrid_model = {
        'xgb': best_xgb,
        'bayes': best_bayes
    }
    joblib.dump(hybrid_model, model_path)
    print(f"Model saved to {model_path}")
    
    # We don't really need meta.json for static RMSE anymore because BayesianRidge
    # calculates dynamic STD per day, but we will save average std just in case.
    meta_path = os.path.join(output_dir, f"{model_name}_meta.json")
    with open(meta_path, 'w') as f:
        json.dump({"rmse_average": float(rmse), "std_average": float(np.mean(stds)), "mae": float(mae)}, f)
    
    return hybrid_model

def run_training(city, project_root):
    # Ścieżki
    data_path = os.path.join(project_root, 'data', f"dataset_{city}.csv")
    if not os.path.exists(data_path):
        print(f"Error: Dataset {data_path} not found.")
        return
        
    df = pd.read_csv(data_path)
    # Ensure sorted by date
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
    
    all_api_features = [c for c in df.columns if '_previous_' in c]
    
    configs = {}
    for conf_name in ["day1_0000", "day1_1200", "day2_0000", "day2_1200"]:
        max_col = f"temperature_2m_max_previous_{conf_name}_ecmwf_ifs"
        min_col = f"temperature_2m_min_previous_{conf_name}_ecmwf_ifs"
        precip_col = f"precipitation_sum_previous_{conf_name}_ecmwf_ifs"
        
        # Blad ecmwf (prawdziwa - prognoza)
        if max_col in df.columns:
            df[f'err_max_{conf_name}'] = df['Max_Temp'] - df[max_col]
            df[f'err_min_{conf_name}'] = df['Min_Temp'] - df[min_col]
            
            df[f'err_max_{conf_name}_lag2'] = df[f'err_max_{conf_name}'].shift(2)
            df[f'err_min_{conf_name}_lag2'] = df[f'err_min_{conf_name}'].shift(2)
            df[f'err_max_{conf_name}_lag3'] = df[f'err_max_{conf_name}'].shift(3)
            df[f'err_min_{conf_name}_lag3'] = df[f'err_min_{conf_name}'].shift(3)
            
            # Suma opadow z ostatnich 3 dni (oparta na API - bez przesunięcia, bo to prognoza wydana w czasie t)
            df[f'precip_sum_3d_{conf_name}'] = df[precip_col].rolling(3).sum()
            
            api_features = [c for c in df.columns if f'_previous_{conf_name}_' in c]
            
            if "day1" in conf_name:
                lag_features = [
                    'Max_Temp_lag2', 'Avg_Temp_lag2', 'Min_Temp_lag2', 'diurnal_range_lag2',
                    f'err_max_{conf_name}_lag2', f'err_min_{conf_name}_lag2',
                    f'precip_sum_3d_{conf_name}'
                ]
            else:
                lag_features = [
                    'Max_Temp_lag3', 'Avg_Temp_lag3', 'Min_Temp_lag3', 'diurnal_range_lag3',
                    f'err_max_{conf_name}_lag3', f'err_min_{conf_name}_lag3',
                    f'precip_sum_3d_{conf_name}'
                ]
            
            # Dodajemy te cechy z powrotem do slownika configs jako X
            configs[conf_name] = api_features + lag_features + ['day_of_year_sin', 'day_of_year_cos', 'Date']

    # Drop rows where API data is entirely missing AFTER shifting
    initial_len = len(df)
    df = df.dropna(subset=all_api_features, how='all').reset_index(drop=True)
    if len(df) < initial_len:
        print(f"Dropped {initial_len - len(df)} rows due to missing Single Runs API data. Remaining: {len(df)}")
    
    # Przeksztalcamy nazwy kolumn z configu na rzeczywiste dataframy X
    configs_df = {conf: df[cols] for conf, cols in configs.items()}
    
    y_max = df['Max_Temp']
    y_min = df['Min_Temp']
    
    models_dir = os.path.join(project_root, 'models')
    
    for conf_name, X_features in configs_df.items():
        if X_features.empty:
            print(f"Skipping {conf_name} - no features available.")
            continue
            
        ecmwf_max_col = f"temperature_2m_max_previous_{conf_name}_ecmwf_ifs"
        ecmwf_min_col = f"temperature_2m_min_previous_{conf_name}_ecmwf_ifs"
        
        # Filtrujemy wiersze, które nie mają nanów dla tej konkretnej konfiguracji
        valid_mask = ~df[ecmwf_max_col].isna()
        
        X_valid = X_features[valid_mask]
        y_max_valid = y_max[valid_mask]
        y_min_valid = y_min[valid_mask]
        ecmwf_max_valid = df[ecmwf_max_col][valid_mask]
        ecmwf_min_valid = df[ecmwf_min_col][valid_mask]
        
        if X_valid.empty:
            continue
        
        # Obliczamy residual (bias), który ma przewidzieć model
        y_max_residual = y_max_valid - ecmwf_max_valid
        y_min_residual = y_min_valid - ecmwf_min_valid
            
        train_model(
            X=X_valid, 
            y_residual=y_max_residual, 
            y_true_absolute=y_max_valid, 
            ecmwf_absolute=ecmwf_max_valid, 
            model_name=f"{city}_model_max_{conf_name}", 
            output_dir=models_dir
        )
        
        train_model(
            X=X_valid, 
            y_residual=y_min_residual, 
            y_true_absolute=y_min_valid, 
            ecmwf_absolute=ecmwf_min_valid, 
            model_name=f"{city}_model_min_{conf_name}", 
            output_dir=models_dir
        )

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Trenowanie modelu hybrydowego XGBoost + Bayesian Ridge.")
    parser.add_argument("--city", type=str, required=True, help="Nazwa miasta (np. dallas)")
    parser.add_argument("--y_dir", type=str, default="y_data", help="Katalog z historycznymi targetami")
    args = parser.parse_args()
    
    city = args.city
    y_dir = args.y_dir
    
    print(f"Rozpoczęcie potoku dla miasta: {city.upper()} (Target: MAX & MIN Temp, Features: ECMWF)")
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    
    run_training(args.city, project_root)
