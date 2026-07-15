import os
import json
import time
import pandas as pd
from datetime import datetime, timedelta, timezone
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

# Konfiguracja sesji HTTP z ponawianiem
session = requests.Session()
retries = Retry(total=3, backoff_factor=0.3, status_forcelist=[ 500, 502, 503, 504 ])
session.mount('https://', HTTPAdapter(max_retries=retries))

def get_slug(template, dt):
    """Zastępuje placeholdery w szablonie sluga odpowiednimi formatami daty."""
    month_name = dt.strftime('%B').lower()
    day = str(dt.day)
    year = str(dt.year)
    return template.format(month=month_name, day=day, year=year)

def fetch_history_for_market(market_slug, target_dt, market_type, tz_str='UTC'):
    """Pobiera historię transakcji z API Polymarketu i resampluje na interwały godzinowe."""
    try:
        res = session.get(f"https://gamma-api.polymarket.com/events?slug={market_slug}", timeout=5)
        if res.status_code != 200 or not res.json():
            return pd.DataFrame()
    except Exception:
        return pd.DataFrame()
    
    ev = res.json()[0]
    
    # Utworzenie pełnego zakresu godzin od startu rynku do końca target_date (czyli target_date+1 00:00)
    market_start_str = ev.get('startDate')
    if market_start_str:
        start_dt = pd.to_datetime(market_start_str).floor('1h')
    else:
        start_dt = pd.to_datetime(target_dt) - timedelta(days=2) # fallback
        start_dt = pd.to_datetime(start_dt).replace(tzinfo=timezone.utc)
        
    local_midnight = pd.Timestamp(target_dt + timedelta(days=1)).tz_localize(tz_str)
    end_dt = local_midnight.tz_convert('UTC').to_pydatetime().replace(tzinfo=timezone.utc) + timedelta(hours=1)
    full_index = pd.date_range(start=start_dt, end=end_dt, freq='1h', name='timestamp')
    
    markets = ev.get('markets', [])
    all_rows = []
    
    for m in markets:
        cond_id = m.get('conditionId')
        group_title = m.get('groupItemTitle', '')
        if not cond_id or not group_title:
            continue
            
        bucket = group_title.replace('°F', '').replace('F', '').replace('°', '').strip()
        
        try:
            c_res = session.get(f"https://clob.polymarket.com/markets/{cond_id}", timeout=5)
            if c_res.status_code != 200: continue
            
            tokens = c_res.json().get('tokens', [])
            yes_token_id = next((t['token_id'] for t in tokens if t['outcome'].upper() == 'YES'), None)
            no_token_id = next((t['token_id'] for t in tokens if t['outcome'].upper() == 'NO'), None)
            
            if not yes_token_id or not no_token_id: 
                continue
            
            y_res = session.get(f"https://clob.polymarket.com/prices-history?market={yes_token_id}&interval=max", timeout=5)
            n_res = session.get(f"https://clob.polymarket.com/prices-history?market={no_token_id}&interval=max", timeout=5)
            
            if y_res.status_code != 200 or n_res.status_code != 200: 
                continue
            
            y_hist = y_res.json().get('history', [])
            n_hist = n_res.json().get('history', [])
            
            if not y_hist or not n_hist:
                continue
            
            df_y = pd.DataFrame(y_hist)
            df_n = pd.DataFrame(n_hist)
            
            df_y['timestamp'] = pd.to_datetime(df_y['t'], unit='s', utc=True)
            df_n['timestamp'] = pd.to_datetime(df_n['t'], unit='s', utc=True)
            
            # Najpierw zwykły resample dla istniejących danych
            df_y = df_y.set_index('timestamp').resample('1h').ffill()
            df_n = df_n.set_index('timestamp').resample('1h').ffill()
            
            # Następnie rozciągamy na pełen zakres od otwarcia rynku do 00:00 dnia następnego
            df_y = df_y.reindex(full_index).ffill().bfill().reset_index()
            df_n = df_n.reindex(full_index).ffill().bfill().reset_index()
            
            # Łączymy wyniki na podstawie timestampu
            df_merged = pd.merge(df_y[['timestamp', 'p']], df_n[['timestamp', 'p']], on='timestamp', suffixes=('_yes', '_no'))
            df_merged = df_merged.dropna(subset=['p_yes', 'p_no'])
            
            for _, row in df_merged.iterrows():
                all_rows.append({
                    'target_date': target_dt.strftime('%Y-%m-%d'),
                    'snapshot_utc': row['timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
                    'market_type': market_type,
                    'bucket': bucket,
                    'prob_yes': round(row['p_yes'], 4),
                    'prob_no': round(row['p_no'], 4)
                })
        except Exception as e:
            print(f"Exception: {e}")
            pass
            
        time.sleep(0.1)  # Bądźmy łagodni dla API
        
    return pd.DataFrame(all_rows)


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(base_dir, 'cities_config.json')
    data_dir = os.path.join(base_dir, 'data')
    
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    
    with open(config_path, 'r') as f:
        cities = json.load(f)
        
    today = datetime.now(timezone.utc).date()
    end_date = today - timedelta(days=2) # Pobieramy dane do 2 dni wstecz
    
    for city, config in cities.items():
        print(f"\n=== Przetwarzanie miasta: {city} ===")
        csv_path = os.path.join(data_dir, f"{city}.csv")
        
        if os.path.exists(csv_path):
            existing_df = pd.read_csv(csv_path)
            if not existing_df.empty:
                max_date_str = existing_df['target_date'].max()
                # Zaczynamy od max_date żeby uzupełnić ewentualne brakujące godziny i nowe rynki
                start_date = datetime.strptime(max_date_str, '%Y-%m-%d').date()
            else:
                start_date = today - timedelta(days=30)
        else:
            existing_df = pd.DataFrame()
            start_date = today - timedelta(days=30)
            
        print(f"[{city}] Pobieranie od {start_date} do {end_date}")
        
        current_date = start_date
        new_data_frames = []
        
        while current_date <= end_date:
            print(f"  -> Pobieranie dla daty docelowej: {current_date}")
            tz_str = config.get('timezone', 'UTC')
            
            # Rynek MAX
            if 'max_slug' in config:
                slug = get_slug(config['max_slug'], current_date)
                df_max = fetch_history_for_market(slug, current_date, 'MAX', tz_str)
                if not df_max.empty:
                    new_data_frames.append(df_max)
                    
            # Rynek MIN
            if 'min_slug' in config:
                slug = get_slug(config['min_slug'], current_date)
                df_min = fetch_history_for_market(slug, current_date, 'MIN', tz_str)
                if not df_min.empty:
                    new_data_frames.append(df_min)
                    
            current_date += timedelta(days=1)
            
        if new_data_frames:
            df_new = pd.concat(new_data_frames, ignore_index=True)
            if not existing_df.empty:
                df_combined = pd.concat([existing_df, df_new], ignore_index=True)
            else:
                df_combined = df_new
                
            # Deduplikacja na podstawie kluczy (żeby nie powielać snapshotów przy inkrementalnym pobieraniu)
            df_combined = df_combined.drop_duplicates(subset=['target_date', 'snapshot_utc', 'market_type', 'bucket'])
            df_combined = df_combined.sort_values(by=['target_date', 'market_type', 'bucket', 'snapshot_utc'])
            
            df_combined.to_csv(csv_path, index=False)
            print(f"[{city}] Zapisano pomyslnie. Plik CSV ma teraz {len(df_combined)} wierszy.")
        else:
            print(f"[{city}] Brak nowych danych do dodania.")

if __name__ == "__main__":
    main()
