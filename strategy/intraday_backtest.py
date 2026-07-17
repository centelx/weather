import os
import argparse
import pandas as pd
import numpy as np

def generate_actuals_from_dataset(city, base_path, use_fahrenheit):
    data_path = os.path.join(base_path, 'data', f"dataset_{city}.csv")
    df = pd.read_csv(data_path)
    df['target_date'] = pd.to_datetime(df['Date']).dt.date.astype(str)
    
    actual_max = df['Max_Temp']
    actual_min = df['Min_Temp']
    
    if use_fahrenheit:
        actual_max = (actual_max * 1.8 + 32).round()
        actual_min = (actual_min * 1.8 + 32).round()
    else:
        actual_max = actual_max.round()
        actual_min = actual_min.round()
        
    return pd.DataFrame({
        'target_date': df['target_date'],
        'actual_max': actual_max,
        'actual_min': actual_min
    })

def run_intraday_backtest():
    parser = argparse.ArgumentParser(description="Intraday (HFT) Backtest")
    parser.add_argument("--city", default="miami", help="Miasto (np. miami)")
    parser.add_argument("--roi_target", type=float, default=0.40, help="Docelowe minimalne ROI (np. 0.40 = 40 procent)")
    parser.add_argument("--bet", type=float, default=100.0, help="Stała liczba akcji (shares)")
    parser.add_argument("--fee_pct", type=float, default=0.02, help="Prowizja giełdowa")
    parser.add_argument("--min_price", type=float, default=0.30, help="Minimalna cena rynkowa by uniknąć longshotów")
    parser.add_argument("--type", choices=['ALL', 'MAX', 'MIN'], default='MAX', help="Typ rynku")
    args = parser.parse_args()
    
    US_CITIES = ['houston', 'dallas', 'chicago', 'sanfrancisco', 'miami', 'lasvegas', 'newyork', 'nyc', 'losangeles', 'denver']
    use_fahrenheit = args.city.lower() in US_CITIES
    
    base_path = r'C:\Users\barto\Desktop\polymarket\weather'
    preds_file = os.path.join(base_path, 'data', 'predictions_intraday', f'predictions_intraday_{args.city}.csv')
    market_file = os.path.join(base_path, 'data', 'intraday_prices', f'intraday_prices_{args.city}.csv')
    
    if not os.path.exists(preds_file) or not os.path.exists(market_file):
        print("Brak wymaganych plików dla Intraday. Uruchom eksport predykcji i skrypt fetch_intraday.")
        return
        
    df_preds = pd.read_csv(preds_file)
    df_market = pd.read_csv(market_file)
    df_actuals = generate_actuals_from_dataset(args.city, base_path, use_fahrenheit)
    
    if args.type != 'ALL':
        df_preds = df_preds[df_preds['type'] == args.type]
        df_market = df_market[df_market['type'] == args.type]
        
    # Czyszczenie i dopasowanie
    if 'bucket' in df_market.columns:
        df_market['bucket'] = df_market['bucket'].str.replace('F', '').str.replace('C', '')
        
    # Merge
    df = pd.merge(df_market, df_preds, on=['target_date', 'type', 'bucket'], how='inner')
    df['target_date'] = pd.to_datetime(df['target_date'])
    df = df.sort_values(['target_date', 'edt_hour'])
    
    unique_dates = df['target_date'].dt.date.unique()
    
    history = []
    bankroll = 1000.0
    
    print(f"--- Start Symulacji Intraday ({args.city.upper()}) ---")
    print(f"Cel ROI: {args.roi_target*100:.1f}%, Typ: {args.type}, Min Price: {args.min_price}")
    
    total_profit = 0.0
    total_cost = 0.0
    
    for date in unique_dates:
        day_df = df[df['target_date'].dt.date == date]
        
        actual_row = df_actuals[df_actuals['target_date'] == str(date)]
        if actual_row.empty: continue
        actual_max = actual_row.iloc[0]['actual_max']
        actual_min = actual_row.iloc[0]['actual_min']
        
        # Inicjalizujemy blokady koszyków dla DANEGO DNIA
        locked_buckets = set()
        
        for _, row in day_df.iterrows():
            hour = row['edt_hour']
            bucket = row['bucket']
            temp_type = row['type']
            
            # 1. Wybór modelu na podstawie godziny (wg dostępności UTC)
            if hour < 14:
                p_model_yes = row['model_probability_0000']
            else:
                p_model_yes = row['model_probability_1200']
                
            p_market_yes_raw = row['market_probability']
            p_market_no_raw = row['market_probability_no'] if 'market_probability_no' in row else np.nan
            
            if pd.isna(p_model_yes) or pd.isna(p_market_yes_raw): continue
            
            if '-' in bucket:
                b_min, b_max = map(float, bucket.split('-'))
                if use_fahrenheit:
                    is_hit = (b_min <= (actual_max if temp_type == 'MAX' else actual_min) <= b_max)
                else:
                    is_hit = (b_min <= (actual_max if temp_type == 'MAX' else actual_min) < b_max)
            else:
                is_hit = False
            
            # --- YES EVALUATION ---
            yes_key = f"{bucket}_YES"
            if yes_key not in locked_buckets:
                p_market_yes = min(0.99, p_market_yes_raw + 0.01) # spread
                if args.min_price <= p_market_yes <= 0.99:
                    cost_yes = p_market_yes * args.bet
                    net_payout = args.bet * (1.0 - args.fee_pct)
                    exp_prof_yes = (p_model_yes * net_payout) - cost_yes
                    roi_yes = exp_prof_yes / cost_yes
                    
                    if roi_yes >= args.roi_target:
                        locked_buckets.add(yes_key)
                        profit = net_payout - cost_yes if is_hit else -cost_yes
                        
                        history.append({
                            'date': str(date),
                            'hour': hour,
                            'type': 'YES',
                            'bucket': bucket,
                            'p_model': p_model_yes,
                            'p_market': p_market_yes,
                            'roi': roi_yes,
                            'cost': cost_yes,
                            'profit': profit,
                            'is_win': is_hit
                        })
            
            # --- NO EVALUATION ---
            no_key = f"{bucket}_NO"
            if no_key not in locked_buckets and pd.notna(p_market_no_raw):
                p_market_no = min(0.99, p_market_no_raw + 0.01) # spread
                p_model_no = 1.0 - p_model_yes
                
                if args.min_price <= p_market_no <= 0.99:
                    cost_no = p_market_no * args.bet
                    net_payout = args.bet * (1.0 - args.fee_pct)
                    exp_prof_no = (p_model_no * net_payout) - cost_no
                    roi_no = exp_prof_no / cost_no
                    
                    if roi_no >= args.roi_target:
                        locked_buckets.add(no_key)
                        profit = net_payout - cost_no if not is_hit else -cost_no
                        
                        history.append({
                            'date': str(date),
                            'hour': hour,
                            'type': 'NO',
                            'bucket': bucket,
                            'p_model': p_model_no,
                            'p_market': p_market_no,
                            'roi': roi_no,
                            'cost': cost_no,
                            'profit': profit,
                            'is_win': not is_hit
                        })
                        
    df_hist = pd.DataFrame(history)
    if df_hist.empty:
        print("Brak otwartych pozycji - przewaga nie przekroczyła progu.")
        return
        
    wins = df_hist['is_win'].sum()
    win_rate = wins / len(df_hist)
    total_cost = df_hist['cost'].sum()
    total_profit = df_hist['profit'].sum()
    final_roi = total_profit / total_cost if total_cost > 0 else 0
    
    print("\n--- RAPORT INTRADAY ---")
    yes_count = (df_hist['type'] == 'YES').sum()
    no_count = (df_hist['type'] == 'NO').sum()
    print(f"Ilość zakładów: {len(df_hist)} (TAK: {yes_count}, NIE: {no_count})")
    print(f"Win Rate:       {win_rate*100:.1f}%")
    print(f"Suma stawek:    ${total_cost:.2f}")
    print(f"Zysk netto:     ${total_profit:.2f}")
    print(f"ROI:            {final_roi*100:.2f}%")
    
    logs_dir = os.path.join(base_path, 'logs', 'intraday_logs')
    os.makedirs(logs_dir, exist_ok=True)
    out_log = os.path.join(logs_dir, f'intraday_log_{args.city}.csv')
    df_hist.to_csv(out_log, index=False)
    print(f"\nZapisano szczegółowy dziennik transakcji do {out_log}")

if __name__ == "__main__":
    run_intraday_backtest()
