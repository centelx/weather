import os
import argparse
import pandas as pd
import numpy as np
from sklearn.linear_model import BayesianRidge
from sklearn.ensemble import RandomForestRegressor
from sklearn.svm import SVR
import xgboost as xgb
import lightgbm as lgb
import catboost as cb
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.model_selection import TimeSeriesSplit, RandomizedSearchCV
import joblib
import json
import warnings
warnings.filterwarnings('ignore')

def train_model(X, y_residual, y_true_absolute, baseline_absolute, model_name, output_dir, algo):
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
    
    print(f"\n--- Training {model_name} ({algo.upper()} + BayesianRidge) ---")
    
    tscv = TimeSeriesSplit(n_splits=3)
    
    if algo == 'lgbm':
        regressor = lgb.LGBMRegressor(random_state=42, n_jobs=1)
        param_dist = {
            'regressor__num_leaves': [15, 31, 50],
            'regressor__learning_rate': [0.01, 0.05, 0.1],
            'regressor__n_estimators': [50, 100, 150]
        }
    elif algo == 'catboost':
        regressor = cb.CatBoostRegressor(random_state=42, verbose=0, thread_count=1)
        param_dist = {
            'regressor__depth': [4, 6, 8],
            'regressor__learning_rate': [0.01, 0.05, 0.1],
            'regressor__iterations': [50, 100, 150]
        }
    elif algo == 'rf':
        regressor = RandomForestRegressor(random_state=42, n_jobs=1)
        param_dist = {
            'regressor__max_depth': [3, 5, None],
            'regressor__n_estimators': [50, 100, 200],
            'regressor__min_samples_leaf': [1, 2, 4]
        }
    elif algo == 'svr':
        regressor = SVR()
        param_dist = {
            'regressor__C': [0.1, 0.5, 1.0, 5.0, 10.0, 50.0, 100.0, 500.0],
            'regressor__gamma': ['scale', 'auto', 0.001, 0.01, 0.1, 0.5, 1.0],
            'regressor__epsilon': [0.001, 0.01, 0.05, 0.1, 0.2, 0.5],
            'regressor__kernel': ['rbf']
        }
    else:
        raise ValueError("Unknown algo")
        
    main_pipeline = Pipeline([
        ('imputer', SimpleImputer(strategy='mean')),
        ('scaler', StandardScaler()),
        ('regressor', regressor)
    ])
    
    bayes_pipeline = Pipeline([
        ('imputer', SimpleImputer(strategy='mean')),
        ('scaler', StandardScaler()),
        ('regressor', BayesianRidge(compute_score=True))
    ])
    
    bayes_param_dist = {
        'regressor__alpha_1': [1e-6, 1e-5, 1e-4, 1e-3],
        'regressor__lambda_1': [1e-6, 1e-5, 1e-4, 1e-3]
    }
    
    search_iters = 280 if algo == 'svr' else 10
    
    main_search = RandomizedSearchCV(
        main_pipeline, param_distributions=param_dist,
        n_iter=search_iters, cv=tscv, scoring='neg_mean_absolute_error',
        random_state=42, n_jobs=1
    )
    main_search.fit(X_train, y_train)
    best_main = main_search.best_estimator_
    
    bayes_search = RandomizedSearchCV(
        bayes_pipeline, param_distributions=bayes_param_dist,
        n_iter=10, cv=tscv, scoring='neg_mean_absolute_error',
        random_state=42, n_jobs=1
    )
    bayes_search.fit(X_train, y_train)
    best_bayes = bayes_search.best_estimator_
    
    print(f"Main Best params: {main_search.best_params_}")
    
    preds_residual = best_main.predict(X_val)
    _, stds = best_bayes.predict(X_val, return_std=True)
    
    preds_absolute = baseline_val.values + preds_residual
    
    mae = mean_absolute_error(y_true_val, preds_absolute)
    rmse = np.sqrt(mean_squared_error(y_true_val, preds_absolute))
    
    print(f"Validation MAE: {mae:.4f}")
    print(f"Validation RMSE: {rmse:.4f}")
    
    os.makedirs(output_dir, exist_ok=True)
    model_path = os.path.join(output_dir, f"{model_name}.pkl")
    hybrid_model = {
        'xgb': best_main,  # Keep the key 'xgb' for backtester compatibility
        'bayes': best_bayes
    }
    joblib.dump(hybrid_model, model_path)
    
    meta_path = os.path.join(output_dir, f"{model_name}_meta.json")
    with open(meta_path, 'w') as f:
        json.dump({"rmse_average": float(rmse), "std_average": float(np.mean(stds)), "mae": float(mae)}, f)
    
    return hybrid_model

def run_training(city, algo, project_root):
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
    
    # We use Ensemble (Mean of GFS and HRRR) as the baseline for these algorithms
    df['baseline_max'] = (df[gfs_max_col] + df[hrrr_max_col]) / 2.0
    df['baseline_min'] = (df[gfs_min_col] + df[hrrr_min_col]) / 2.0
    
    y_max_residual = df['Max_Temp'] - df['baseline_max']
    y_min_residual = df['Min_Temp'] - df['baseline_min']
    
    models_dir = os.path.join(project_root, 'models_opt')
    X = df[features]
    
    train_model(X, y_max_residual, df['Max_Temp'], df['baseline_max'], f"{city}_model_max_aws_{algo}", models_dir, algo)
    train_model(X, y_min_residual, df['Min_Temp'], df['baseline_min'], f"{city}_model_min_aws_{algo}", models_dir, algo)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Trenowanie alternatywnych modeli ML.")
    parser.add_argument("--city", type=str, required=True, help="Nazwa miasta")
    parser.add_argument("--algo", type=str, choices=['lgbm', 'catboost', 'rf', 'svr'], required=True, help="Algorytm ML")
    args = parser.parse_args()
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    run_training(args.city, args.algo, project_root)
