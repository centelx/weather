import os
import json
import numpy as np
import pandas as pd
import joblib
import xgboost as xgb
from sklearn.svm import SVR
from sklearn.linear_model import BayesianRidge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import RobustScaler
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.model_selection import TimeSeriesSplit, RandomizedSearchCV

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
models_dir = os.path.join(project_root, 'summer_models')
os.makedirs(models_dir, exist_ok=True)

def get_data(city, filter_months=None):
    data_path = os.path.join(project_root, 'data_aws', f"dataset_{city}.csv")
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
    features = api_features + lag_features + ['day_of_year_sin', 'day_of_year_cos']
    
    df = df.dropna(subset=features + ['Date']).reset_index(drop=True)
    
    if filter_months:
        df = df[df['Date'].dt.month.isin(filter_months)].reset_index(drop=True)
        
    df['baseline_max'] = (df[gfs_max_col] + df[hrrr_max_col]) / 2.0
    df['baseline_min'] = (df[gfs_min_col] + df[hrrr_min_col]) / 2.0
    
    return df, features

def run_training(X_train, y_train, X_val, y_true_val, baseline_val, model_name, algo_type="svr"):
    tscv = TimeSeriesSplit(n_splits=3)
    
    if algo_type == "svr":
        regressor = SVR()
        param_dist = {
            'regressor__C': [0.1, 1.0, 10.0, 50.0, 100.0],
            'regressor__gamma': ['scale', 'auto', 0.1, 0.01, 0.001],
            'regressor__kernel': ['rbf']
        }
    elif algo_type == "xgb":
        regressor = xgb.XGBRegressor(objective='reg:squarederror', random_state=42)
        param_dist = {
            'regressor__n_estimators': [50, 100, 150, 200, 300],
            'regressor__max_depth': [2, 3, 4, 5, 6],
            'regressor__learning_rate': [0.01, 0.05, 0.1, 0.2]
        }
    else:
        raise ValueError("Unsupported algo_type")
        
    # UZYWAMY ROBUST SCALER!
    main_pipeline = Pipeline([
        ('imputer', SimpleImputer(strategy='mean')),
        ('scaler', RobustScaler()),
        ('regressor', regressor)
    ])
    
    bayes_pipeline = Pipeline([
        ('imputer', SimpleImputer(strategy='mean')),
        ('scaler', RobustScaler()),
        ('regressor', BayesianRidge(compute_score=True))
    ])
    
    search = RandomizedSearchCV(
        main_pipeline, param_distributions=param_dist,
        n_iter=25 if algo_type == "svr" else 50, cv=tscv, scoring='neg_mean_absolute_error',
        random_state=42, n_jobs=1
    )
    search.fit(X_train, y_train)
    best_main = search.best_estimator_
    
    bayes_param_dist = {
        'regressor__alpha_1': [1e-6, 1e-5, 1e-4],
        'regressor__lambda_1': [1e-6, 1e-5, 1e-4]
    }
    bayes_search = RandomizedSearchCV(
        bayes_pipeline, param_distributions=bayes_param_dist,
        n_iter=9, cv=tscv, scoring='neg_mean_absolute_error',
        random_state=42, n_jobs=1
    )
    bayes_search.fit(X_train, y_train)
    best_bayes = bayes_search.best_estimator_
    
    preds_residual = best_main.predict(X_val)
    preds_absolute = baseline_val.values + preds_residual
    
    mae = mean_absolute_error(y_true_val, preds_absolute)
    rmse = np.sqrt(mean_squared_error(y_true_val, preds_absolute))
    
    return f"{model_name}: MAE {mae:.4f}, RMSE {rmse:.4f}"

if __name__ == "__main__":
    rankings_file = os.path.join(project_root, "models_opt", "feature_rankings.json")
    with open(rankings_file, 'r') as f:
        rankings = json.load(f)

    results = []

    # 1. MIAMI (Trained ONLY on May-Oct, Validated on May-Oct 2025) - XGBoost + RobustScaler
    df_m, all_features_m = get_data("miami", filter_months=[5, 6, 7, 8, 9, 10])
    val_mask_m = (df_m['Date'] >= pd.to_datetime('2025-05-01')) & (df_m['Date'] <= pd.to_datetime('2025-10-31'))
    train_mask_m = ~val_mask_m
    
    X_train_m = df_m[train_mask_m][all_features_m]
    X_val_m = df_m[val_mask_m][all_features_m]
    
    y_train_m_max = df_m[train_mask_m]["Max_Temp"] - df_m[train_mask_m]["baseline_max"]
    r_m_max_xgb = run_training(X_train_m, y_train_m_max, X_val_m, df_m[val_mask_m]["Max_Temp"], df_m[val_mask_m]["baseline_max"], "miami_max_robust_xgb", "xgb")
    results.append(r_m_max_xgb)

    y_train_m_min = df_m[train_mask_m]["Min_Temp"] - df_m[train_mask_m]["baseline_min"]
    r_m_min_xgb = run_training(X_train_m, y_train_m_min, X_val_m, df_m[val_mask_m]["Min_Temp"], df_m[val_mask_m]["baseline_min"], "miami_min_robust_xgb", "xgb")
    results.append(r_m_min_xgb)

    summary_path = os.path.join(current_dir, "summer_8.txt")
    with open(summary_path, 'w') as f:
        f.write("WYNIKI - TEST ROBUST SCALER + XGBoost (MIAMI Maj-Paź)\n")
        f.write("-----------------------------------------------------------\n")
        f.write("MIAMI (Trained: May-Oct, Test: May-Oct 2025):\n")
        f.write(f"- MAX (XGBoost N=ALL): {results[0]}\n")
        f.write(f"- MIN (XGBoost N=ALL): {results[1]}\n")
    
    print("Wytrenowano modele Miami XGBoost z RobustScaler!")
