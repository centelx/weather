import os
import pandas as pd
import numpy as np
from sklearn.linear_model import BayesianRidge
import xgboost as xgb
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error

def evaluate_features(df, feature_cols, target, ecmwf_col):
    df_val = df.dropna(subset=feature_cols + [target, ecmwf_col])
    split_idx = int(len(df_val) * 0.8)
    
    train_df = df_val.iloc[:split_idx]
    test_df = df_val.iloc[split_idx:]
    
    X_train = train_df[feature_cols]
    y_train = train_df[target] - train_df[ecmwf_col]
    
    X_test = test_df[feature_cols]
    y_test = test_df[target]
    ecmwf_test = test_df[ecmwf_col]
    
    model = Pipeline([
        ('imputer', SimpleImputer(strategy='mean')),
        ('scaler', StandardScaler()),
        ('regressor', xgb.XGBRegressor(random_state=42, n_estimators=100, max_depth=3, learning_rate=0.05))
    ])
    
    model.fit(X_train, y_train)
    preds = ecmwf_test + model.predict(X_test)
    mae = mean_absolute_error(y_test, preds)
    return mae

def main():
    df = pd.read_csv('data/dataset_nyc.csv')
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values('Date').reset_index(drop=True)
    
    df['day_of_year'] = df['Date'].dt.dayofyear
    df['day_of_year_sin'] = np.sin(2 * np.pi * df['day_of_year'] / 365.25)
    df['day_of_year_cos'] = np.cos(2 * np.pi * df['day_of_year'] / 365.25)
    
    conf = "day1_1200"
    api_cols = [c for c in df.columns if f'_previous_{conf}_' in c]
    
    max_col = f"temperature_2m_max_previous_{conf}_ecmwf_ifs"
    min_col = f"temperature_2m_min_previous_{conf}_ecmwf_ifs"
    
    df['err_max'] = df['Max_Temp'] - df[max_col]
    df['err_min'] = df['Min_Temp'] - df[min_col]
    
    # Lag 1 and 2
    for i in range(1, 5):
        df[f'Max_Temp_lag{i}'] = df['Max_Temp'].shift(i)
        df[f'Min_Temp_lag{i}'] = df['Min_Temp'].shift(i)
        df[f'Avg_Temp_lag{i}'] = df['Avg_Temp'].shift(i)
        df[f'err_max_lag{i}'] = df['err_max'].shift(i)
        df[f'err_min_lag{i}'] = df['err_min'].shift(i)
    
    base_features = api_cols + ['day_of_year_sin', 'day_of_year_cos', 
                                'Max_Temp_lag1', 'Avg_Temp_lag1', 'Min_Temp_lag1', 'err_max_lag1', 'err_min_lag1', 
                                'Max_Temp_lag2', 'Avg_Temp_lag2', 'Min_Temp_lag2', 'err_max_lag2', 'err_min_lag2']
    
    # Feature for MIN
    precip_col = f"precipitation_sum_previous_{conf}_ecmwf_ifs"
    df['precip_sum_3d'] = df[precip_col].shift(1).rolling(3).sum()
    
    # Feature for MAX
    df['diurnal_range_lag1'] = df['Max_Temp_lag1'] - df['Min_Temp_lag1']
    
    base_features_lag1_only = api_cols + ['day_of_year_sin', 'day_of_year_cos', 
                                          'Max_Temp_lag1', 'Avg_Temp_lag1', 'Min_Temp_lag1', 'err_max_lag1', 'err_min_lag1']
    
    print("--- MIN TEMPERATURE EXPERIMENTS ---")
    min_best_feat = base_features + ['precip_sum_3d']
    mae_min_best = evaluate_features(df, min_best_feat, 'Min_Temp', min_col)
    print(f"Current Best (Lag1+2 + Precip3d): {mae_min_best:.4f}")
    
    min_lag1_feat = base_features_lag1_only + ['precip_sum_3d']
    mae_min_lag1 = evaluate_features(df, min_lag1_feat, 'Min_Temp', min_col)
    print(f"Exp (Only Lag1 + Precip3d): {mae_min_lag1:.4f} -> {'IMPROVED' if mae_min_lag1 < mae_min_best else 'WORSE'}")
    
    print("\n--- MAX TEMPERATURE EXPERIMENTS ---")
    max_best_feat = base_features + ['diurnal_range_lag1']
    mae_max_best = evaluate_features(df, max_best_feat, 'Max_Temp', max_col)
    print(f"Current Best (Lag1+2 + Diurnal1): {mae_max_best:.4f}")
    
    max_lag1_feat = base_features_lag1_only + ['diurnal_range_lag1']
    mae_max_lag1 = evaluate_features(df, max_lag1_feat, 'Max_Temp', max_col)
    print(f"Exp (Only Lag1 + Diurnal1): {mae_max_lag1:.4f} -> {'IMPROVED' if mae_max_lag1 < mae_max_best else 'WORSE'}")

if __name__ == '__main__':
    main()
