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

def train_model(X, y_residual, y_true_absolute, baseline_absolute, model_name, output_dir):
    X = X.sort_index()
    y_residual = y_residual.sort_index()
    y_true_absolute = y_true_absolute.sort_index()
    baseline_absolute = baseline_absolute.sort_index()
    
    split_date = pd.to_datetime('2026-04-01')
    
    train_mask = X['Date'] < split_date
    val_mask = X['Date'] >= split_date
    
    X_train = X[train_mask].drop(columns=['Date'])
    X_val = X[val_mask].drop(columns=['Date'])
    y_train, y_val = y_residual[train_mask], y_residual[val_mask]
    y_true_val = y_true_absolute[val_mask]
    baseline_val = baseline_absolute[val_mask]
    
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
    
    xgb_search = RandomizedSearchCV(
        xgb_pipeline, param_distributions=xgb_param_dist,
        n_iter=10, cv=tscv, scoring='neg_mean_absolute_error',
        random_state=42, n_jobs=1
    )
    xgb_search.fit(X_train, y_train)
    best_xgb = xgb_search.best_estimator_
    
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
    
    preds_absolute = baseline_val.values + preds_residual
    
    mae = mean_absolute_error(y_true_val, preds_absolute)
    rmse = np.sqrt(mean_squared_error(y_true_val, preds_absolute))
    
    print(f"Validation Absolute MAE: {mae:.2f}")
    print(f"Validation Absolute RMSE: {rmse:.2f}")
    print(f"Average Model Confidence (Dynamic RMSE/STD): {np.mean(stds):.2f}")
    
    os.makedirs(output_dir, exist_ok=True)
    model_path = os.path.join(output_dir, f"{model_name}.pkl")
    hybrid_model = {
        'xgb': best_xgb,
        'bayes': best_bayes
    }
    joblib.dump(hybrid_model, model_path)
    print(f"Model saved to {model_path}")
    
    meta_path = os.path.join(output_dir, f"{model_name}_meta.json")
    with open(meta_path, 'w') as f:
        json.dump({"rmse_average": float(rmse), "std_average": float(np.mean(stds)), "mae": float(mae)}, f)
    
    return hybrid_model

def run_training(city, source, project_root):
    data_path = os.path.join(project_root, 'data_aws', f"dataset_{city}.csv")
    if not os.path.exists(data_path):
        print(f"Error: Dataset {data_path} not found.")
        return
        
    df = pd.read_csv(data_path)
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values('Date').reset_index(drop=True)
    
    day_of_year = df['Date'].dt.dayofyear
    df['day_of_year_sin'] = np.sin(2 * np.pi * day_of_year / 365.25)
    df['day_of_year_cos'] = np.cos(2 * np.pi * day_of_year / 365.25)
    
    df['Max_Temp_lag2'] = df['Max_Temp'].shift(2)
    df['Avg_Temp_lag2'] = df['Avg_Temp'].shift(2)
    df['Min_Temp_lag2'] = df['Min_Temp'].shift(2)
    
    df['diurnal_range_lag2'] = df['Max_Temp_lag2'] - df['Min_Temp_lag2']
    
    # Model predictions columns from API (day1_1200)
    gfs_max_col = "temperature_2m_max_previous_day1_1200_gfs"
    gfs_min_col = "temperature_2m_min_previous_day1_1200_gfs"
    gfs_precip_col = "precipitation_sum_previous_day1_1200_gfs"
    
    hrrr_max_col = "temperature_2m_max_previous_day1_1200_hrrr"
    hrrr_min_col = "temperature_2m_min_previous_day1_1200_hrrr"
    hrrr_precip_col = "precipitation_sum_previous_day1_1200_hrrr"
    
    # Calculate model specific errors vs truth
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
    
    initial_len = len(df)
    # Drop rows where any of the base features are missing
    df = df.dropna(subset=features, how='any').reset_index(drop=True)
    if len(df) < initial_len:
        print(f"Dropped {initial_len - len(df)} rows due to missing features/lags. Remaining: {len(df)}")
    
    # Calculate baseline
    if source == 'gfs':
        df['baseline_max'] = df[gfs_max_col]
        df['baseline_min'] = df[gfs_min_col]
    elif source == 'hrrr':
        df['baseline_max'] = df[hrrr_max_col]
        df['baseline_min'] = df[hrrr_min_col]
    else:
        df['baseline_max'] = (df[gfs_max_col] + df[hrrr_max_col]) / 2.0
        df['baseline_min'] = (df[gfs_min_col] + df[hrrr_min_col]) / 2.0
    
    y_max_residual = df['Max_Temp'] - df['baseline_max']
    y_min_residual = df['Min_Temp'] - df['baseline_min']
    
    models_dir = os.path.join(project_root, 'models_opt')
    
    X = df[features]
    
    train_model(
        X=X, 
        y_residual=y_max_residual, 
        y_true_absolute=df['Max_Temp'], 
        baseline_absolute=df['baseline_max'], 
        model_name=f"{city}_model_max_aws_{source}", 
        output_dir=models_dir
    )
    
    train_model(
        X=X, 
        y_residual=y_min_residual, 
        y_true_absolute=df['Min_Temp'], 
        baseline_absolute=df['baseline_min'], 
        model_name=f"{city}_model_min_aws_{source}", 
        output_dir=models_dir
    )

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Trenowanie połączonego modelu hybrydowego XGBoost + Bayesian Ridge.")
    parser.add_argument("--city", type=str, required=True, help="Nazwa miasta (np. dallas)")
    parser.add_argument("--source", type=str, choices=['gfs', 'hrrr'], required=True, help="Źródło bazowe (gfs lub hrrr)")
    args = parser.parse_args()
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    
    print(f"Rozpoczęcie potoku dla miasta: {args.city.upper()} (Model: {args.source.upper()})")
    run_training(args.city, args.source, project_root)
