import os
import requests
import pandas as pd
from datetime import datetime, timezone
import time

def generate_slugs(target_date, city="nyc"):
    """Generuje deterministyczne slugi na podstawie daty."""
    dt = pd.to_datetime(target_date)
    month_name = dt.strftime('%B').lower()
    day = dt.day
    year = dt.year
    
    city_str = "new-york-city" if city == "nyc" else city
    
    slug_max = f"highest-temperature-in-{city_str}-on-{month_name}-{day}-{year}"
    slug_min = f"lowest-temperature-in-{city_str}-on-{month_name}-{day}-{year}"
    
    if city == "nyc":
        return [
            (f"highest-temperature-in-nyc-on-{month_name}-{day}-{year}", 'MAX'),
            (f"lowest-temperature-in-nyc-on-{month_name}-{day}-{year}", 'MIN'),
            (slug_max, 'MAX'),
            (slug_min, 'MIN')
        ]
    else:
        return [
            (slug_max, 'MAX'),
            (slug_min, 'MIN')
        ]

def fetch_real_polymarket_data(base_path, city):
    preds_file = os.path.join(base_path, f'predictions_history_{city}.csv')
    if not os.path.exists(preds_file):
        print(f"Brak pliku {preds_file}.")
        return
        
    df_preds = pd.read_csv(preds_file)
    unique_dates = df_preds['target_date'].unique()
    
    out_records = []
    
    session = requests.Session()
    
    for date_str in unique_dates:
        print(f"Przetwarzanie daty: {date_str}...")
        slugs_to_try = generate_slugs(date_str, city)
        
        found_max = False
        found_min = False
        
        for slug, temp_type in slugs_to_try:
            if temp_type == 'MAX' and found_max: continue
            if temp_type == 'MIN' and found_min: continue
                
            url_events = f"https://gamma-api.polymarket.com/events?slug={slug}"
            try:
                res = session.get(url_events, timeout=10)
            except Exception as e:
                print(f"Error fetching {url_events}: {e}")
                continue
            
            if res.status_code == 200 and len(res.json()) > 0:
                ev = res.json()[0]
                markets = ev.get('markets', [])
                print(f"  Znaleziono wydarzenie: {ev.get('title')}")
                
                for m in markets:
                    cond_id = m.get('conditionId')
                    group_title = m.get('groupItemTitle', '')
                    
                    # Parsowanie koszyków dla F i C
                    if 'C' in group_title or '°C' in group_title:
                        # W przypadku Taipei i C mamy "29°C" lub "29°C or below"
                        b_str = group_title.replace('°C', '').replace('C', '').replace(' or below', '').replace(' or higher', '').strip()
                        try:
                            val = int(b_str)
                            final_bucket = f"{val}-{val+1}"
                        except ValueError:
                            final_bucket = group_title.replace('°C', '').replace('C', '')
                    else:
                        # Przypadek dla NYC i F: "80-81°F"
                        final_bucket = group_title.replace('°F', '').replace('F', '').replace('°', '')
                        
                    # 1. Pobranie token_id z CLOB
                    url_clob = f"https://clob.polymarket.com/markets/{cond_id}"
                    try:
                        c_res = session.get(url_clob, timeout=10)
                    except Exception:
                        continue
                    if c_res.status_code != 200: continue
                    
                    c_data = c_res.json()
                    tokens = c_data.get('tokens', [])
                    
                    yes_token_id = next((t['token_id'] for t in tokens if t['outcome'].upper() == 'YES'), None)
                    no_token_id = next((t['token_id'] for t in tokens if t['outcome'].upper() == 'NO'), None)
                    
                    if not yes_token_id or not no_token_id: continue
                    
                    try:
                        # Pobieramy historię YES
                        h_res_yes = session.get("https://clob.polymarket.com/prices-history", params={"market": yes_token_id, "interval": "max"}, timeout=10)
                        # Pobieramy historię NO
                        h_res_no = session.get("https://clob.polymarket.com/prices-history", params={"market": no_token_id, "interval": "max"}, timeout=10)
                    except Exception:
                        continue
                    
                    if h_res_yes.status_code != 200 or h_res_no.status_code != 200: continue
                    
                    hist_yes = h_res_yes.json().get('history', [])
                    hist_no = h_res_no.json().get('history', [])
                    
                    if not hist_yes or not hist_no: continue
                    
                    df_hist_yes = pd.DataFrame(hist_yes)
                    df_hist_yes['t'] = pd.to_datetime(df_hist_yes['t'], unit='s', utc=True)
                    df_hist_yes = df_hist_yes.sort_values('t').reset_index(drop=True)
                    
                    df_hist_no = pd.DataFrame(hist_no)
                    df_hist_no['t'] = pd.to_datetime(df_hist_no['t'], unit='s', utc=True)
                    df_hist_no = df_hist_no.sort_values('t').reset_index(drop=True)
                    
                    target_dt = datetime.strptime(f"{date_str} 23:59:59", "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
                    
                    for horizon in [1, 2]:
                        cutoff_dt = target_dt - pd.Timedelta(days=horizon)
                        df_f_yes = df_hist_yes[df_hist_yes['t'] <= cutoff_dt]
                        df_f_no = df_hist_no[df_hist_no['t'] <= cutoff_dt]
                        
                        if not df_f_yes.empty and not df_f_no.empty:
                            price_yes = df_f_yes.iloc[-1]['p']
                            price_no = df_f_no.iloc[-1]['p']
                            
                            out_records.append({
                                'target_date': date_str,
                                'forecast_horizon': horizon,
                                'type': temp_type,
                                'bucket': final_bucket,
                                'market_probability': float(price_yes),
                                'market_probability_no': float(price_no)
                            })
                            
                if temp_type == 'MAX': found_max = True
                if temp_type == 'MIN': found_min = True
                time.sleep(0.2) # Rate limiting
                
    df_out = pd.DataFrame(out_records)
    out_csv = os.path.join(base_path, f'real_polymarket_prices_{city}_with_no.csv')
    df_out.to_csv(out_csv, index=False)
    print(f"\nZakończono pobieranie! Wyniki zapisano do {out_csv}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--city", default="taipei")
    args = parser.parse_args()
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    fetch_real_polymarket_data(project_root, city=args.city)
