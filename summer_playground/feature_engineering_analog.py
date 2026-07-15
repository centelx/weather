import os
import json
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.svm import SVR
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler, RobustScaler
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import TimeSeriesSplit, RandomizedSearchCV
from sklearn.neighbors import NearestNeighbors

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)

def add_analog_errors(df, train_mask, k=10):
    gfs_max = "temperature_2m_max_previous_day1_1200_gfs"
    gfs_min = "temperature_2m_min_previous_day1_1200_gfs"
    gfs_mean = "temperature_2m_mean_previous_day1_1200_gfs"
    hrrr_max = "temperature_2m_max_previous_day1_1200_hrrr"
    hrrr_min = "temperature_2m_min_previous_day1_1200_hrrr"
    hrrr_mean = "temperature_2m_mean_previous_day1_1200_hrrr"
    
    features_for_knn = [gfs_max, gfs_min, gfs_mean, hrrr_max, hrrr_min, hrrr_mean]
    scaler = StandardScaler()
    scaled_features = scaler.fit_transform(df[features_for_knn])
    
    err_max_gfs = df['Max_Temp'] - df[gfs_max]
    err_max_hrrr = df['Max_Temp'] - df[hrrr_max]
    err_min_gfs = df['Min_Temp'] - df[gfs_min]
    err_min_hrrr = df['Min_Temp'] - df[hrrr_min]
    
    analog_err_max_gfs = np.zeros(len(df))
    analog_err_max_hrrr = np.zeros(len(df))
    analog_err_min_gfs = np.zeros(len(df))
    analog_err_min_hrrr = np.zeros(len(df))
    
    for i in range(len(df)):
        current_date = df['Date'].iloc[i]
        is_train = train_mask.iloc[i]
        
        pool_mask = train_mask.copy()
        
        if is_train:
            exclude_mask = (df['Date'] >= current_date - pd.Timedelta(days=7)) & \
                           (df['Date'] <= current_date + pd.Timedelta(days=7))
            pool_mask = pool_mask & (~exclude_mask)
            
        if pool_mask.sum() < k:
            analog_err_max_gfs[i] = 0
            analog_err_max_hrrr[i] = 0
            analog_err_min_gfs[i] = 0
            analog_err_min_hrrr[i] = 0
            continue
            
        pool_indices = np.where(pool_mask)[0]
        X_pool = scaled_features[pool_indices]
        
        nn = NearestNeighbors(n_neighbors=k, metric='euclidean')
        nn.fit(X_pool)
        
        X_query = scaled_features[i].reshape(1, -1)
        distances, indices_in_pool = nn.kneighbors(X_query)
        
        actual_indices = pool_indices[indices_in_pool[0]]
        
        analog_err_max_gfs[i] = err_max_gfs.iloc[actual_indices].mean()
        analog_err_max_hrrr[i] = err_max_hrrr.iloc[actual_indices].mean()
        analog_err_min_gfs[i] = err_min_gfs.iloc[actual_indices].mean()
        analog_err_min_hrrr[i] = err_min_hrrr.iloc[actual_indices].mean()
        
    df['analog_err_max_gfs'] = analog_err_max_gfs
    df['analog_err_max_hrrr'] = analog_err_max_hrrr
    df['analog_err_min_gfs'] = analog_err_min_gfs
    df['analog_err_min_hrrr'] = analog_err_min_hrrr
    
    return df

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
        df['precip_sum_3d_gfs'] = df[gfs_precip_col].rolling(3).sum()
        df['precip_sum_3d_hrrr'] = df[hrrr_precip_col].rolling(3).sum()
        
    api_features = [c for c in df.columns if '_previous_' in c]
    lag_features = [
        'Max_Temp_lag2', 'Avg_Temp_lag2', 'Min_Temp_lag2', 'diurnal_range_lag2',
        'precip_sum_3d_gfs', 'precip_sum_3d_hrrr'
    ]
    
    base_all_features = api_features + lag_features + ['day_of_year_sin', 'day_of_year_cos']
    df = df.dropna(subset=base_all_features + ['Date']).reset_index(drop=True)
    
    if filter_months:
        df = df[df['Date'].dt.month.isin(filter_months)].reset_index(drop=True)
        
    df['baseline_max'] = (df[gfs_max_col] + df[hrrr_max_col]) / 2.0
    df['baseline_min'] = (df[gfs_min_col] + df[hrrr_min_col]) / 2.0
    
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
        n_iter = 15
    elif algo_type == "xgb":
        regressor = xgb.XGBRegressor(objective='reg:squarederror', random_state=42)
        param_dist = {
            'regressor__n_estimators': [50, 100, 150, 200],
            'regressor__max_depth': [2, 3, 4, 5],
            'regressor__learning_rate': [0.01, 0.05, 0.1, 0.2]
        }
        n_iter = 25
        
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

def get_base_optimal_features(ranking_list):
    clean = []
    for f in ranking_list:
        if f.startswith('err_'):
            continue
        clean.append(f)
    return clean

if __name__ == "__main__":
    rankings_file = os.path.join(project_root, "models_opt", "feature_rankings.json")
    with open(rankings_file, 'r') as f:
        rankings = json.load(f)

    out_file = os.path.join(current_dir, "analog_errors_results.txt")
    with open(out_file, "w") as f:
        f.write("WYNIKI OPTYMALIZACJI: METODA ANALOGOW (KNN)\n")
        f.write("============================================================\n\n")

    # 1. MIAMI MAX
    print("Running MIAMI...")
    df_m, base_all_m = get_data("miami", filter_months=[5, 6, 7, 8, 9, 10])
    val_m = (df_m['Date'] >= pd.to_datetime('2025-05-01')) & (df_m['Date'] <= pd.to_datetime('2025-10-31'))
    tr_m = ~val_m
    
    df_m = add_analog_errors(df_m, tr_m, k=10)
    
    opt_m_max = get_base_optimal_features(rankings["miami_max"][:24]) + ["analog_err_max_gfs", "analog_err_max_hrrr"]
    y_tr_m_max = df_m[tr_m]["Max_Temp"] - df_m[tr_m]["baseline_max"]
    y_val_m_max = df_m[val_m]["Max_Temp"]
    base_val_m_max = df_m[val_m]["baseline_max"]
    
    mae_m_max = run_training(df_m[tr_m][opt_m_max], y_tr_m_max, df_m[val_m][opt_m_max], y_val_m_max, base_val_m_max, "svr", "standard")
    
    # 2. MIAMI MIN
    feat_m_min = base_all_m + ["analog_err_min_gfs", "analog_err_min_hrrr"]
    y_tr_m_min = df_m[tr_m]["Min_Temp"] - df_m[tr_m]["baseline_min"]
    y_val_m_min = df_m[val_m]["Min_Temp"]
    base_val_m_min = df_m[val_m]["baseline_min"]
    
    mae_m_min = run_training(df_m[tr_m][feat_m_min], y_tr_m_min, df_m[val_m][feat_m_min], y_val_m_min, base_val_m_min, "xgb", "robust")
    
    # 3. LA MAX
    print("Running LA...")
    df_la, base_all_la = get_data("losangeles", filter_months=None)
    val_la = ((df_la['Date'] >= pd.to_datetime('2025-06-01')) & (df_la['Date'] <= pd.to_datetime('2025-09-30'))) | (df_la['Date'] >= pd.to_datetime('2026-06-01'))
    tr_la = ~val_la
    
    df_la = add_analog_errors(df_la, tr_la, k=10)
    
    opt_la_max = get_base_optimal_features(rankings["losangeles_max"][:12]) + ["analog_err_max_gfs", "analog_err_max_hrrr"]
    y_tr_la_max = df_la[tr_la]["Max_Temp"] - df_la[tr_la]["baseline_max"]
    y_val_la_max = df_la[val_la]["Max_Temp"]
    base_val_la_max = df_la[val_la]["baseline_max"]
    
    mae_la_max = run_training(df_la[tr_la][opt_la_max], y_tr_la_max, df_la[val_la][opt_la_max], y_val_la_max, base_val_la_max, "svr", "robust")

    # 4. LA MIN
    feat_la_min = base_all_la + ["analog_err_min_gfs", "analog_err_min_hrrr"]
    y_tr_la_min = df_la[tr_la]["Min_Temp"] - df_la[tr_la]["baseline_min"]
    y_val_la_min = df_la[val_la]["Min_Temp"]
    base_val_la_min = df_la[val_la]["baseline_min"]
    
    mae_la_min = run_training(df_la[tr_la][feat_la_min], y_tr_la_min, df_la[val_la][feat_la_min], y_val_la_min, base_val_la_min, "xgb", "robust")
    
    with open(out_file, "a") as f:
        f.write(f"1. MIAMI MAX (SVR, StandardScaler): MAE = {mae_m_max:.4f}\n")
        f.write(f"2. MIAMI MIN (XGBoost, RobustScaler): MAE = {mae_m_min:.4f}\n")
        f.write(f"3. LA MAX (SVR, RobustScaler): MAE = {mae_la_max:.4f}\n")
        f.write(f"4. LA MIN (XGBoost, RobustScaler): MAE = {mae_la_min:.4f}\n")
        
    print("Testy Analog Ensemble zakonczone. Wyniki w analog_errors_results.txt")
