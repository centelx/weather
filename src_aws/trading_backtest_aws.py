import os
import argparse
import pandas as pd
import numpy as np

from backtester_aws import Backtester

def generate_dummy_market_data(df_preds):
    df_market = df_preds[['target_date', 'forecast_horizon', 'type', 'bucket', 'model_probability']].copy()
    np.random.seed(42)
    noise = np.random.uniform(-0.10, 0.10, len(df_market))
    df_market['market_probability'] = df_market['model_probability'] + noise
    df_market['market_probability'] = df_market['market_probability'].clip(0.01, 0.99)
    df_market = df_market.drop(columns=['model_probability'])
    return df_market

def generate_actuals_from_dataset(city, base_path, use_fahrenheit):
    data_path = os.path.join(base_path, 'data_aws', f"dataset_{city}.csv")
    df = pd.read_csv(data_path)
    df['target_date'] = pd.to_datetime(df['Date']).dt.date.astype(str)
    
    actual_max = df['Max_Temp']
    actual_min = df['Min_Temp']
    
    if use_fahrenheit:
        actual_max = np.floor(actual_max * 1.8 + 32 + 0.5)
        actual_min = np.floor(actual_min * 1.8 + 32 + 0.5)
    else:
        actual_max = np.floor(actual_max + 0.5)
        actual_min = np.floor(actual_min + 0.5)
        
    return pd.DataFrame({
        'target_date': df['target_date'],
        'actual_max': actual_max,
        'actual_min': actual_min
    })

def main():
    parser = argparse.ArgumentParser(description="Automatyczny Backtest Giełdowy na danych Polymarket (AWS)")
    parser.add_argument("--city", default="miami")
    parser.add_argument("-f", "--fahrenheit", action="store_true")
    parser.add_argument("--edge", type=float, default=0.05)
    parser.add_argument("--bet", type=float, default=20.0)
    parser.add_argument("--min_price", type=float, default=0.30)
    parser.add_argument("--max_price", type=float, default=0.99)
    parser.add_argument("--polymarket_csv", type=str, default="")
    parser.add_argument("--type", choices=['ALL', 'MAX', 'MIN'], default='ALL')
    parser.add_argument("--side", choices=['ALL', 'YES', 'NO'], default='ALL')
    args = parser.parse_args()
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    base_path = os.path.dirname(current_dir)
    preds_file = os.path.join(base_path, f'predictions_history_{args.city}_aws.csv')
    
    if not os.path.exists(preds_file):
        print(f"Błąd: Brak pliku z predykcjami {preds_file}.")
        return
        
    print("Wczytywanie predykcji modelu (AWS)...")
    df_preds = pd.read_csv(preds_file)
    
    print("Wczytywanie prawdziwych rozstrzygnięć pogody (AWS)...")
    df_actuals = generate_actuals_from_dataset(args.city, base_path, args.fahrenheit)
    
    if args.polymarket_csv and os.path.exists(args.polymarket_csv):
        print(f"Wczytywanie historycznych cen rynkowych z {args.polymarket_csv}...")
        df_market = pd.read_csv(args.polymarket_csv)
        if 'bucket' in df_market.columns:
            df_market['bucket'] = df_market['bucket'].str.replace('F', '')
        # Dopasowujemy do nazwy z predykcji aws
        df_market['forecast_horizon'] = 'aws_day1_1200'
    else:
        print("Generowanie wyimaginowanych cen rynkowych Polymarket...")
        df_market = generate_dummy_market_data(df_preds)
        
    if args.type != 'ALL':
        df_preds = df_preds[df_preds['type'] == args.type].copy()
        if not df_market.empty:
            df_market = df_market[df_market['type'] == args.type].copy()
            
    engine = Backtester(
        df_preds=df_preds,
        df_market=df_market,
        df_actuals=df_actuals,
        initial_bankroll=1000.0,
        edge_threshold=args.edge,
        bet_size=args.bet,
        fee_pct=0.02,
        min_price=args.min_price,
        max_price=args.max_price,
        side=args.side
    )
    
    engine.run()
    
    # Save reports to a dedicated aws folder
    reports_dir = os.path.join(base_path, 'reports_aws')
    os.makedirs(reports_dir, exist_ok=True)
    engine.generate_report(reports_dir)

if __name__ == "__main__":
    main()
