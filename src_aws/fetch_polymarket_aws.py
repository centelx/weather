import os
import sys
import pandas as pd
from datetime import datetime, timezone, timedelta
import time
import argparse

# Dodajemy projektowy root do sys.path żeby zaimportować z src
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.polymarket_api import PolymarketAPI

def generate_slugs(target_date, city="miami"):
    dt = pd.to_datetime(target_date)
    month_name = dt.strftime('%B').lower()
    day = dt.day
    year = dt.year
    
    city_str = city
    if city == "sanfrancisco":
        city_str = "san-francisco"
    elif city == "losangeles":
        city_str = "los-angeles"
    elif city == "newyork":
        city_str = "new-york"
    
    slug_max = f"highest-temperature-in-{city_str}-on-{month_name}-{day}-{year}"
    slug_min = f"lowest-temperature-in-{city_str}-on-{month_name}-{day}-{year}"
    
    return [
        (slug_max, 'MAX'),
        (slug_min, 'MIN')
    ]

def fetch_data_for_aws(base_path, city):
    api = PolymarketAPI()
    
    preds_file = os.path.join(base_path, f'predictions_history_{city}_aws.csv')
    if not os.path.exists(preds_file):
        print(f"Brak pliku {preds_file}. Odpal najpierw export_history_aws.py")
        return
        
    df_preds = pd.read_csv(preds_file)
    unique_dates = df_preds['target_date'].unique()
    
    out_records = []
    
    for date_str in unique_dates:
        print(f"Przetwarzanie daty rozstrzygnięcia: {date_str}...")
        slugs_to_try = generate_slugs(date_str, city)
        
        # T-1 o 16:00 UTC (12:00 EDT / 12:00 czasu z wybiegu z Anglii po opublikowaniu)
        target_dt = pd.to_datetime(f"{date_str} 00:00:00").tz_localize('UTC')
        day_before = target_dt - pd.Timedelta(days=1)
        cutoff_dt = day_before + pd.Timedelta(hours=16) # T-1 16:00:00 UTC
        
        for slug, temp_type in slugs_to_try:
            ev = api.get_event_by_slug(slug)
            if not ev:
                continue
                
            print(f"  Znaleziono wydarzenie: {ev.get('title')}")
            markets = ev.get('markets', [])
            
            for m in markets:
                cond_id = m.get('conditionId')
                group_title = m.get('groupItemTitle', '')
                
                # Parsowanie nazwy koszyka na kompatybilną z modelem
                if 'C' in group_title or '°C' in group_title:
                    b_str = group_title.replace('°C', '').replace('C', '').replace(' or below', '').replace(' or higher', '').strip()
                    try:
                        val = int(b_str)
                        final_bucket = f"{val}-{val+1}"
                    except ValueError:
                        final_bucket = group_title.replace('°C', '').replace('C', '')
                else:
                    final_bucket = group_title.replace('°F', '').replace('F', '').replace('°', '')
                    
                # Pobranie cen YES i NO dla wybranej godziny (cutoff_dt)
                try:
                    c_res = api.session.get(f"{api.CLOB_URL}/markets/{cond_id}", timeout=10)
                    if c_res.status_code != 200: continue
                    
                    tokens = c_res.json().get('tokens', [])
                    yes_token_id = next((t['token_id'] for t in tokens if t['outcome'].upper() == 'YES'), None)
                    no_token_id = next((t['token_id'] for t in tokens if t['outcome'].upper() == 'NO'), None)
                    
                    if not yes_token_id or not no_token_id: continue
                    
                    df_hist_yes = api.get_price_history(yes_token_id, interval="max")
                    df_hist_no = api.get_price_history(no_token_id, interval="max")
                    
                    if df_hist_yes.empty or df_hist_no.empty: continue
                    
                    df_f_yes = df_hist_yes[df_hist_yes['timestamp'] <= cutoff_dt]
                    df_f_no = df_hist_no[df_hist_no['timestamp'] <= cutoff_dt]
                    
                    if not df_f_yes.empty and not df_f_no.empty:
                        price_yes = df_f_yes.iloc[-1]['price']
                        price_no = df_f_no.iloc[-1]['price']
                        
                        out_records.append({
                            'target_date': date_str,
                            'forecast_horizon': 'aws_day1_1200',
                            'type': temp_type,
                            'bucket': final_bucket,
                            'market_probability': float(price_yes),
                            'market_probability_no': float(price_no)
                        })
                except Exception as e:
                    print(f"Błąd przetwarzania rynku: {e}")
                    
            time.sleep(0.2)
            
    if not out_records:
        print("Nie znaleziono żadnych danych historycznych z tego API.")
        return
        
    df_out = pd.DataFrame(out_records)
    data_dir = os.path.join(base_path, 'data_aws')
    os.makedirs(data_dir, exist_ok=True)
    out_csv = os.path.join(data_dir, f'real_market_prices_{city}_aws.csv')
    df_out.to_csv(out_csv, index=False)
    print(f"\nZakończono pobieranie! Wyniki zapisano do {out_csv} ({len(df_out)} wierszy)")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--city", default="miami")
    args = parser.parse_args()
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    fetch_data_for_aws(project_root, city=args.city)
