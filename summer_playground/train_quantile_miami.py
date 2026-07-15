import os
import json
import numpy as np
import pandas as pd
from sklearn.svm import SVR
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.model_selection import KFold
import lightgbm as lgb
from scipy.interpolate import PchipInterpolator

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)

def get_bucket_probs_from_quantiles(q15, q50, q85):
    # Punkty CDF
    # Dodajemy sztuczne kotwice (tzw. ogony) żeby funkcja nie "odleciała" na zewnątrz
    x = [q50 - 4*(q50 - q15), q15, q50, q85, q50 + 4*(q85 - q50)]
    y = [0.001, 0.15, 0.50, 0.85, 0.999]
    
    # Sortowanie żeby upewnić się, że X idzie w górę (chociaż powinien)
    points = sorted(zip(x, y))
    x = [p[0] for p in points]
    y = [p[1] for p in points]
    
    # PchipInterpolator gwarantuje monotoniczność (CDF zawsze rośnie)
    cdf_interp = PchipInterpolator(x, y)
    
    # Definiujemy koszyki w okolicy Q50
    center_even = int(np.round(q50)) // 2 * 2
    buckets = [center_even - 4, center_even - 2, center_even, center_even + 2, center_even + 4]
    
    res = []
    for b in buckets:
        # Granice w skali całkowitej np. dla koszyka 90 (90-91) granice to 89.5 i 91.5
        lower = b - 0.5
        upper = b + 1.5
        
        # Prawdopodobieństwo to pole pod krzywą (różnica dystrybuanty)
        prob = cdf_interp(upper) - cdf_interp(lower)
        prob = max(0.0, float(prob)) # Zabezpieczenie przed błędem precyzji zmiennoprzecinkowej
        res.append((f"{b}-{b+1}", prob))
        
    # Sortujemy malejąco po prawdopodobieństwie
    res = sorted(res, key=lambda item: item[1], reverse=True)
    return res

def run():
    print("Ładowanie danych...")
    data_path = os.path.join(project_root, 'data_aws', 'dataset_miami.csv')
    df = pd.read_csv(data_path)
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values('Date').reset_index(drop=True)
    
    # Obliczamy baseline
    gfs_max_col = "temperature_2m_max_previous_day1_1200_gfs"
    hrrr_max_col = "temperature_2m_max_previous_day1_1200_hrrr"
    gfs_min_col = "temperature_2m_min_previous_day1_1200_gfs"
    hrrr_min_col = "temperature_2m_min_previous_day1_1200_hrrr"
    
    df['baseline_max'] = (df[gfs_max_col] + df[hrrr_max_col]) / 2.0
    df['baseline_min'] = (df[gfs_min_col] + df[hrrr_min_col]) / 2.0
    
    df['day_of_year'] = df['Date'].dt.dayofyear
    df['day_of_year_sin'] = np.sin(2 * np.pi * df['day_of_year'] / 365.25)
    df['day_of_year_cos'] = np.cos(2 * np.pi * df['day_of_year'] / 365.25)
    
    df['Max_Temp_lag2'] = df['Max_Temp'].shift(2)
    df['Avg_Temp_lag2'] = df['Avg_Temp'].shift(2)
    df['Min_Temp_lag2'] = df['Min_Temp'].shift(2)
    df['diurnal_range_lag2'] = df['Max_Temp_lag2'] - df['Min_Temp_lag2']
    
    gfs_precip_col = "precipitation_sum_previous_day1_1200_gfs"
    hrrr_precip_col = "precipitation_sum_previous_day1_1200_hrrr"
    if gfs_precip_col in df.columns:
        df['precip_sum_3d_gfs'] = df[gfs_precip_col].rolling(3).sum()
    if hrrr_precip_col in df.columns:
        df['precip_sum_3d_hrrr'] = df[hrrr_precip_col].rolling(3).sum()
        
    # Wczytujemy zoptymalizowane cechy (24 najlepsze)
    rankings_file = os.path.join(project_root, "models_opt", "feature_rankings.json")
    with open(rankings_file, 'r') as f:
        rankings = json.load(f)
    features_m1 = [f for f in rankings["miami_max"] if not f.startswith('err_')][:24]
    
    df = df.dropna(subset=features_m1 + ['Max_Temp']).reset_index(drop=True)
    y_target = df['Max_Temp'] - df['baseline_max']
    
    # ==========================================
    # KROK 1: K-Fold Out-Of-Fold błędy Modelu 1
    # ==========================================
    print("Krok 1: Generowanie błędów Modelu 1 (Out-Of-Fold)...")
    model1 = Pipeline([
        ('imputer', SimpleImputer(strategy='mean')),
        ('scaler', StandardScaler()),
        ('regressor', SVR(C=10.0, gamma='scale', kernel='rbf'))
    ])
    
    kf = KFold(n_splits=5, shuffle=False)
    oof_preds = np.zeros(len(df))
    X_m1 = df[features_m1]
    
    for train_idx, val_idx in kf.split(X_m1):
        X_train, X_val = X_m1.iloc[train_idx], X_m1.iloc[val_idx]
        y_train = y_target.iloc[train_idx]
        model1.fit(X_train, y_train)
        oof_preds[val_idx] = model1.predict(X_val)
        
    df['err_model1'] = y_target - oof_preds
    
    # Lagujemy błędy dla Modelu 2 (zgodnie z prośbą: 2, 3 i 4 dni temu)
    df['err_m1_lag2'] = df['err_model1'].shift(2)
    df['err_m1_lag3'] = df['err_model1'].shift(3)
    df['err_m1_lag4'] = df['err_model1'].shift(4)
    
    df = df.dropna(subset=['err_m1_lag4']).reset_index(drop=True)
    
    # ==========================================
    # KROK 2: Przygotowanie Danych do Regresji Kwantylowej
    # ==========================================
    features_m2 = features_m1 + ['err_m1_lag2', 'err_m1_lag3', 'err_m1_lag4']
    y_target_m2 = df['Max_Temp'] - df['baseline_max']
    
    test_start = pd.to_datetime('2026-06-14')
    test_end = pd.to_datetime('2026-07-08')
    
    df_test_period = df[(df['Date'] >= test_start) & (df['Date'] <= test_end)].copy()
    
    out_path = os.path.join(current_dir, 'miami_max_quantile_june_july.txt')
    
    print("Krok 2: Daily Retraining (Regresja Kwantylowa)...")
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write("--- PREDYKCJE MIAMI MAX (14 czerwca - 8 lipca 2026) ---\n")
        f.write("Wygenerowane przez: Regresja Kwantylowa (LightGBM) + Interpolacja Asymetryczna CDF\n")
        f.write("Cechy dodatkowe: Błąd Modelu 1 z przed 2, 3 i 4 dni.\n\n")
        
        for idx, row in df_test_period.iterrows():
            current_date = row['Date']
            date_str = current_date.strftime('%Y-%m-%d')
            prev_date_str = (current_date - pd.Timedelta(days=1)).strftime('%Y-%m-%d')
            
            # Trenujemy na wszystkim sprzed 'dzisiaj'
            train_mask = df['Date'] < current_date
            X_train = df.loc[train_mask, features_m2]
            y_train = y_target_m2.loc[train_mask]
            
            X_test = df.loc[[idx], features_m2]
            
            # Trenujemy 3 modele kwantylowe (15%, 50%, 85%)
            # Uwaga: parametry alpha definiują percentyle (0.15 = 15%)
            lgb_15 = lgb.LGBMRegressor(objective='quantile', alpha=0.15, n_estimators=100, learning_rate=0.05, max_depth=3, random_state=42, verbose=-1)
            lgb_50 = lgb.LGBMRegressor(objective='quantile', alpha=0.50, n_estimators=100, learning_rate=0.05, max_depth=3, random_state=42, verbose=-1)
            lgb_85 = lgb.LGBMRegressor(objective='quantile', alpha=0.85, n_estimators=100, learning_rate=0.05, max_depth=3, random_state=42, verbose=-1)
            
            lgb_15.fit(X_train, y_train)
            lgb_50.fit(X_train, y_train)
            lgb_85.fit(X_train, y_train)
            
            pred_15_resid = lgb_15.predict(X_test)[0]
            pred_50_resid = lgb_50.predict(X_test)[0]
            pred_85_resid = lgb_85.predict(X_test)[0]
            
            # Zmiana błędu na wartość absolutną temperatury
            baseline = row['baseline_max']
            pred_15 = (baseline + pred_15_resid) * 1.8 + 32
            pred_50 = (baseline + pred_50_resid) * 1.8 + 32
            pred_85 = (baseline + pred_85_resid) * 1.8 + 32
            
            # Mapowanie na koszyki Polymarketu
            buckets = get_bucket_probs_from_quantiles(pred_15, pred_50, pred_85)
            
            # Znalezienie 3 najbardziej prawdopodobnych (tak jak poprzednio)
            main_bucket = buckets[0]
            other_buckets = buckets[1:3]
            
            f.write(f"Data celu: {date_str} (przewidziano: {prev_date_str} po runie 1200)\n")
            f.write(f" -> Główna predykcja: {main_bucket[0]} °F (Szansa: {main_bucket[1]*100:.1f}%)\n")
            
            others_str = ", ".join([f"{b[0]} °F ({b[1]*100:.1f}%)" for b in other_buckets])
            f.write(f" -> Sąsiednie koszyki: {others_str}\n")
            
            # Informacyjnie dodajemy jak wygląda kwantyl, żeby udowodnić asymetrię
            f.write(f" -> [Debug] Kwantyle: Q15={pred_15:.1f}F | Q50={pred_50:.1f}F | Q85={pred_85:.1f}F\n")
            f.write("-" * 40 + "\n")
            
    print(f"Zakończono pomyślnie. Zapisano do: {out_path}")

if __name__ == "__main__":
    run()
