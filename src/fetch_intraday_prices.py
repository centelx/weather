import os
import requests
import pandas as pd
from datetime import datetime, timezone, timedelta
import time

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

def fetch_intraday_data(base_path, city):
    # Domyślnie bierzemy daty z naszego exportu intraday
    preds_file = os.path.join(base_path, 'data', 'predictions_intraday', f'predictions_intraday_{city}.csv')
    if not os.path.exists(preds_file):
        print(f"Brak pliku {preds_file}. Odpal najpierw export_intraday_preds.py")
        return
        
    df_preds = pd.read_csv(preds_file)
    unique_dates = df_preds['target_date'].unique()
    unique_dates = [d for d in unique_dates if d >= '2026-06-10']
    
    out_records = []
    session = requests.Session()
    
    # 14 snapshots: 10:00 EDT to 24:00 EDT (which is 15 snapshots actually: 10,11,12,13,14,15,16,17,18,19,20,21,22,23,24)
    # EDT is UTC-4. So 10:00 EDT = 14:00 UTC.
    
    for date_str in unique_dates:
        print(f"Przetwarzanie daty: {date_str}...")
        slugs_to_try = generate_slugs(date_str, city)
        
        target_dt = pd.to_datetime(f"{date_str} 00:00:00").tz_localize('UTC')
        day_before = target_dt - pd.Timedelta(days=1)
        
        # Generowanie timestampów (UTC) dla godzin 10:00 - 24:00 EDT
        # 10:00 EDT = 14:00 UTC (na T-1)
        # ...
        # 24:00 EDT = 04:00 UTC (na T)
        snapshot_dts = []
        for h in range(10, 25):
            utc_hour = (h + 4) % 24
            utc_day_offset = (h + 4) // 24
            
            snap_dt = day_before + pd.Timedelta(days=utc_day_offset, hours=utc_hour)
            snapshot_dts.append((h, snap_dt))
        
        found_max = False
        found_min = False
        
        for slug, temp_type in slugs_to_try:
            if temp_type == 'MAX' and found_max: continue
            if temp_type == 'MIN' and found_min: continue
                
            url_events = f"https://gamma-api.polymarket.com/events?slug={slug}"
            try:
                res = session.get(url_events, timeout=10)
            except Exception as e:
                continue
            
            if res.status_code == 200 and len(res.json()) > 0:
                ev = res.json()[0]
                markets = ev.get('markets', [])
                print(f"  Znaleziono wydarzenie: {ev.get('title')}")
                
                for m in markets:
                    cond_id = m.get('conditionId')
                    group_title = m.get('groupItemTitle', '')
                    
                    if 'C' in group_title or '°C' in group_title:
                        b_str = group_title.replace('°C', '').replace('C', '').replace(' or below', '').replace(' or higher', '').strip()
                        try:
                            val = int(b_str)
                            final_bucket = f"{val}-{val+1}"
                        except ValueError:
                            final_bucket = group_title.replace('°C', '').replace('C', '')
                    else:
                        final_bucket = group_title.replace('°F', '').replace('F', '').replace('°', '')
                        
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
                        h_res_yes = session.get("https://clob.polymarket.com/prices-history", params={"market": yes_token_id, "interval": "max"}, timeout=10)
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
                    
                    for edt_hour, cutoff_dt in snapshot_dts:
                        df_f_yes = df_hist_yes[df_hist_yes['t'] <= cutoff_dt]
                        df_f_no = df_hist_no[df_hist_no['t'] <= cutoff_dt]
                        
                        if not df_f_yes.empty and not df_f_no.empty:
                            price_yes = df_f_yes.iloc[-1]['p']
                            price_no = df_f_no.iloc[-1]['p']
                            
                            out_records.append({
                                'target_date': date_str,
                                'edt_hour': edt_hour,
                                'type': temp_type,
                                'bucket': final_bucket,
                                'market_probability': float(price_yes),
                                'market_probability_no': float(price_no)
                            })
                            
                if temp_type == 'MAX': found_max = True
                if temp_type == 'MIN': found_min = True
                time.sleep(0.2)
                
    df_out = pd.DataFrame(out_records)
    data_dir = os.path.join(base_path, 'data', 'intraday_prices')
    os.makedirs(data_dir, exist_ok=True)
    out_csv = os.path.join(data_dir, f'intraday_prices_{city}.csv')
    df_out.to_csv(out_csv, index=False)
    print(f"\nZakończono pobieranie! Wyniki zapisano do {out_csv}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--city", default="miami")
    args = parser.parse_args()
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    fetch_intraday_data(project_root, city=args.city)
