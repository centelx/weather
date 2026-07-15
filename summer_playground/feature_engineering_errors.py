import os
import json
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.svm import SVR
from sklearn.linear_model import BayesianRidge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler, RobustScaler
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.model_selection import TimeSeriesSplit, RandomizedSearchCV

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)

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
        err_max_gfs = df['Max_Temp'] - df[gfs_max_col]
        err_min_gfs = df['Min_Temp'] - df[gfs_min_col]
        err_max_hrrr = df['Max_Temp'] - df[hrrr_max_col]
        err_min_hrrr = df['Min_Temp'] - df[hrrr_min_col]
        
        # Generujemy lagi od lag2 do lag8 (od 1 do 7 dni dostępnej historii)
        for i in range(2, 9):
            df[f'err_max_gfs_lag{i}'] = err_max_gfs.shift(i)
            df[f'err_min_gfs_lag{i}'] = err_min_gfs.shift(i)
            df[f'err_max_hrrr_lag{i}'] = err_max_hrrr.shift(i)
            df[f'err_min_hrrr_lag{i}'] = err_min_hrrr.shift(i)
        
        df['precip_sum_3d_gfs'] = df[gfs_precip_col].rolling(3).sum()
        df['precip_sum_3d_hrrr'] = df[hrrr_precip_col].rolling(3).sum()
        
    api_features = [c for c in df.columns if '_previous_' in c]
    lag_features = [
        'Max_Temp_lag2', 'Avg_Temp_lag2', 'Min_Temp_lag2', 'diurnal_range_lag2',
        'precip_sum_3d_gfs', 'precip_sum_3d_hrrr'
    ]
    
    all_lags = []
    for i in range(2, 9):
        all_lags.extend([f'err_max_gfs_lag{i}', f'err_min_gfs_lag{i}', f'err_max_hrrr_lag{i}', f'err_min_hrrr_lag{i}'])
        
    features_for_dropna = api_features + lag_features + ['day_of_year_sin', 'day_of_year_cos'] + all_lags
    df = df.dropna(subset=features_for_dropna + ['Date']).reset_index(drop=True)
    
    if filter_months:
        df = df[df['Date'].dt.month.isin(filter_months)].reset_index(drop=True)
        
    df['baseline_max'] = (df[gfs_max_col] + df[hrrr_max_col]) / 2.0
    df['baseline_min'] = (df[gfs_min_col] + df[hrrr_min_col]) / 2.0
    
    base_all_features = api_features + lag_features + ['day_of_year_sin', 'day_of_year_cos']
    return df, base_all_features

def run_training(X_train, y_train, X_val, y_true_val, baseline_val, algo_type, scaler_type):
    tscv = TimeSeriesSplit(n_splits=3)
    
    if algo_type == "svr":
        regressor = SVR()
        param_dist = {
            'regressor__C': [0.1, 1.0, 10.0, 50.0],
            'regressor__gamma': ['scale', 'auto', 0.1, 0.01],
            'regressor__kernel': ['rbf']
        }
        n_iter = 12
    elif algo_type == "xgb":
        regressor = xgb.XGBRegressor(objective='reg:squarederror', random_state=42)
        param_dist = {
            'regressor__n_estimators': [50, 100, 150, 200],
            'regressor__max_depth': [2, 3, 4, 5],
            'regressor__learning_rate': [0.01, 0.05, 0.1, 0.2]
        }
        n_iter = 20
        
    scaler = StandardScaler() if scaler_type == "standard" else RobustScaler()
    
    main_pipeline = Pipeline([
        ('imputer', SimpleImputer(strategy='mean')),
        ('scaler', scaler),
        ('regressor', regressor)
    ])
    
    search = RandomizedSearchCV(
        main_pipeline, param_distributions=param_dist,
        n_iter=n_iter, cv=tscv, scoring='neg_mean_absolute_error',
        random_state=42, n_jobs=1
    )
    search.fit(X_train, y_train)
    best_main = search.best_estimator_
    
    preds_residual = best_main.predict(X_val)
    preds_absolute = baseline_val.values + preds_residual
    
    mae = mean_absolute_error(y_true_val, preds_absolute)
    return mae

def get_base_optimal_features(ranking_list, target_type):
    clean = []
    for f in ranking_list:
        if f.startswith(f'err_{target_type}'):
            continue
        clean.append(f)
    return clean

if __name__ == "__main__":
    rankings_file = os.path.join(project_root, "models_opt", "feature_rankings.json")
    with open(rankings_file, 'r') as f:
        rankings = json.load(f)

    out_file = os.path.join(current_dir, "last_errors_all.txt")
    with open(out_file, "w") as f:
        f.write("WYNIKI OPTYMALIZACJI HISTORII BLEDOW (1 do 7 dni)\n")
        f.write("="*60 + "\n\n")

    # 1. MIAMI MAX: SVR + StandardScaler, May-Oct
    df_m, base_all_m = get_data("miami", filter_months=[5, 6, 7, 8, 9, 10])
    val_m = (df_m['Date'] >= pd.to_datetime('2025-05-01')) & (df_m['Date'] <= pd.to_datetime('2025-10-31'))
    tr_m = ~val_m
    
    opt_m_max = get_base_optimal_features(rankings["miami_max"][:24], "max")
    y_tr = df_m[tr_m]["Max_Temp"] - df_m[tr_m]["baseline_max"]
    y_val = df_m[val_m]["Max_Temp"]
    base_val = df_m[val_m]["baseline_max"]
    
    results = []
    for n in range(1, 8):
        err_feats = [f"err_max_gfs_lag{i}" for i in range(2, 2+n)] + [f"err_max_hrrr_lag{i}" for i in range(2, 2+n)]
        curr_feats = list(set(opt_m_max + err_feats))
        mae = run_training(df_m[tr_m][curr_feats], y_tr, df_m[val_m][curr_feats], y_val, base_val, "svr", "standard")
        results.append(mae)
    
    with open(out_file, "a") as f:
        f.write("1. MIAMI MAX (SVR + StandardScaler, May-Oct)\n")
        for n, mae in enumerate(results, 1):
            f.write(f"   {n} dni w historii: MAE = {mae:.4f}\n")
        f.write("\n")

    # 2. MIAMI MIN: XGBoost + RobustScaler, May-Oct
    y_tr = df_m[tr_m]["Min_Temp"] - df_m[tr_m]["baseline_min"]
    y_val = df_m[val_m]["Min_Temp"]
    base_val = df_m[val_m]["baseline_min"]
    
    results = []
    for n in range(1, 8):
        err_feats = [f"err_min_gfs_lag{i}" for i in range(2, 2+n)] + [f"err_min_hrrr_lag{i}" for i in range(2, 2+n)]
        curr_feats = list(set(base_all_m + err_feats))
        mae = run_training(df_m[tr_m][curr_feats], y_tr, df_m[val_m][curr_feats], y_val, base_val, "xgb", "robust")
        results.append(mae)
        
    with open(out_file, "a") as f:
        f.write("2. MIAMI MIN (XGBoost + RobustScaler, May-Oct)\n")
        for n, mae in enumerate(results, 1):
            f.write(f"   {n} dni w historii: MAE = {mae:.4f}\n")
        f.write("\n")

    # 3. LA MAX: SVR + RobustScaler, All Data
    df_la, base_all_la = get_data("losangeles", filter_months=None)
    val_la = ((df_la['Date'] >= pd.to_datetime('2025-06-01')) & (df_la['Date'] <= pd.to_datetime('2025-09-30'))) | (df_la['Date'] >= pd.to_datetime('2026-06-01'))
    tr_la = ~val_la
    
    opt_la_max = get_base_optimal_features(rankings["losangeles_max"][:12], "max")
    y_tr = df_la[tr_la]["Max_Temp"] - df_la[tr_la]["baseline_max"]
    y_val = df_la[val_la]["Max_Temp"]
    base_val = df_la[val_la]["baseline_max"]
    
    results = []
    for n in range(1, 8):
        err_feats = [f"err_max_gfs_lag{i}" for i in range(2, 2+n)] + [f"err_max_hrrr_lag{i}" for i in range(2, 2+n)]
        curr_feats = list(set(opt_la_max + err_feats))
        mae = run_training(df_la[tr_la][curr_feats], y_tr, df_la[val_la][curr_feats], y_val, base_val, "svr", "robust")
        results.append(mae)

    with open(out_file, "a") as f:
        f.write("3. LA MAX (SVR + RobustScaler, All Data)\n")
        for n, mae in enumerate(results, 1):
            f.write(f"   {n} dni w historii: MAE = {mae:.4f}\n")
        f.write("\n")
        
    # 4. LA MIN: XGBoost + RobustScaler, All Data
    y_tr = df_la[tr_la]["Min_Temp"] - df_la[tr_la]["baseline_min"]
    y_val = df_la[val_la]["Min_Temp"]
    base_val = df_la[val_la]["baseline_min"]
    
    results = []
    for n in range(1, 8):
        err_feats = [f"err_min_gfs_lag{i}" for i in range(2, 2+n)] + [f"err_min_hrrr_lag{i}" for i in range(2, 2+n)]
        curr_feats = list(set(base_all_la + err_feats))
        mae = run_training(df_la[tr_la][curr_feats], y_tr, df_la[val_la][curr_feats], y_val, base_val, "xgb", "robust")
        results.append(mae)
        
    with open(out_file, "a") as f:
        f.write("4. LA MIN (XGBoost + RobustScaler, All Data)\n")
        for n, mae in enumerate(results, 1):
            f.write(f"   {n} dni w historii: MAE = {mae:.4f}\n")
        f.write("\n")
        
    print("Testy zakończone. Wyniki w last_errors_all.txt")
