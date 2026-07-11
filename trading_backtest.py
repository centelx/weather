import os
import argparse
import pandas as pd
import numpy as np

# Zastępujemy starą logikę modułową architekturą
from src.polymarket_api import PolymarketAPI
from src.backtester import Backtester

def generate_dummy_market_data(df_preds):
    """
    Generuje sztuczne dane rynkowe z Polymarket na potrzeby testów, 
    ponieważ darmowe API Gamma/CLOB ma ograniczenia przy głębokim wczytywaniu historii bez token_ids.
    """
    df_market = df_preds[['target_date', 'forecast_horizon', 'type', 'bucket', 'model_probability']].copy()
    np.random.seed(42)
    noise = np.random.uniform(-0.10, 0.10, len(df_market))
    df_market['market_probability'] = df_market['model_probability'] + noise
    df_market['market_probability'] = df_market['market_probability'].clip(0.01, 0.99)
    df_market = df_market.drop(columns=['model_probability'])
    return df_market

def generate_actuals_from_dataset(city, base_path, use_fahrenheit):
    """Pobiera rzeczywiste wartości temperatur z datasetu bazowego."""
    data_path = os.path.join(base_path, 'data', f"dataset_{city}.csv")
    df = pd.read_csv(data_path)
    df['target_date'] = pd.to_datetime(df['Date']).dt.date.astype(str)
    
    actual_max = df['Max_Temp']
    actual_min = df['Min_Temp']
    
    if use_fahrenheit:
        actual_max = actual_max * 1.8 + 32
        actual_min = actual_min * 1.8 + 32
        
    return pd.DataFrame({
        'target_date': df['target_date'],
        'actual_max': actual_max,
        'actual_min': actual_min
    })

def main():
    parser = argparse.ArgumentParser(description="Automatyczny Backtest Giełdowy na danych Polymarket")
    parser.add_argument("--city", default="nyc", help="Miasto (np. nyc, taipei)")
    parser.add_argument("-f", "--fahrenheit", action="store_true", help="Rozliczaj w Fahrenheitach")
    parser.add_argument("--edge", type=float, default=0.05, help="Próg wejścia (Edge)")
    parser.add_argument("--bet", type=float, default=20.0, help="Stała stawka w USD")
    parser.add_argument("--min_price", type=float, default=0.30, help="Minimalna cena")
    parser.add_argument("--max_price", type=float, default=0.99, help="Maksymalna cena")
    parser.add_argument("--polymarket_csv", type=str, default="", help="Ścieżka do prawdziwych danych rynkowych z API/Grafu")
    parser.add_argument("--type", choices=['ALL', 'MAX', 'MIN'], default='ALL', help="Filtruj wg typu rynku")
    args = parser.parse_args()
    
    base_path = r'C:\Users\barto\Desktop\polymarket\weather'
    preds_file = os.path.join(base_path, f'predictions_history_{args.city}.csv')
    
    if not os.path.exists(preds_file):
        print(f"Błąd: Brak pliku z predykcjami {preds_file}. Odpal najpierw export_history.py")
        return
        
    print("Wczytywanie predykcji modelu...")
    df_preds = pd.read_csv(preds_file)
    
    print("Wczytywanie prawdziwych rozstrzygnięć pogody...")
    df_actuals = generate_actuals_from_dataset(args.city, base_path, args.fahrenheit)
    
    # Podłączenie do API Polymarket / lub pliku
    # W rzeczywistym scenariuszu, pętla przez df_preds, pobranie token_id z API Gamma i strzał do CLOB
    # zrobiliśmy klasę PolymarketAPI w src/polymarket_api.py, aby łatwo podpinać tokeny!
    
    if args.polymarket_csv and os.path.exists(args.polymarket_csv):
        print(f"Wczytywanie prawdziwych cen Polymarket z {args.polymarket_csv} ...")
        df_market = pd.read_csv(args.polymarket_csv)
        # Usuwamy literkę "F" z koszyków (np. "82-83F" -> "82-83"), aby pasowały do naszych predykcji
        if 'bucket' in df_market.columns:
            df_market['bucket'] = df_market['bucket'].str.replace('F', '')
    else:
        print("Nie podano pliku z tokenami. Używamy wbudowanego generatora cen Polymarket (fallback API/dummy)...")
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
        fee_pct=0.02,  # 2% prowizji z zysku na Polymarket
        min_price=args.min_price,
        max_price=args.max_price
    )
    
    engine.run()
    engine.generate_report(base_path)

if __name__ == "__main__":
    main()
