import os
import time
import pandas as pd
from datetime import datetime, timedelta, timezone
import requests

session = requests.Session()

def get_slug(template, dt):
    month_name = dt.strftime('%B').lower()
    day = str(dt.day)
    year = str(dt.year)
    return template.format(month=month_name, day=day, year=year)

def fetch_and_test():
    target_dt = datetime.strptime('2026-07-10', '%Y-%m-%d').date()
    slug = get_slug("highest-temperature-in-miami-on-{month}-{day}-{year}", target_dt)
    
    print(f"Pobieranie dla: {slug}")
    res = session.get(f"https://gamma-api.polymarket.com/events?slug={slug}")
    if res.status_code != 200 or not res.json():
        print("Nie znaleziono rynku!")
        return
        
    ev = res.json()[0]
    
    market_start_str = ev.get('startDate')
    if market_start_str:
        start_dt = pd.to_datetime(market_start_str).floor('1h')
    else:
        start_dt = pd.to_datetime(target_dt) - timedelta(days=2)
        start_dt = pd.to_datetime(start_dt).replace(tzinfo=timezone.utc)
        
    local_midnight = pd.Timestamp(target_dt + timedelta(days=1)).tz_localize('America/New_York')
    end_dt = local_midnight.tz_convert('UTC').to_pydatetime().replace(tzinfo=timezone.utc)
    full_index = pd.date_range(start=start_dt, end=end_dt, freq='1h', name='timestamp')
    
    markets = ev.get('markets', [])
    all_raw_rows = []
    all_resampled_rows = []
    
    for m in markets:
        cond_id = m.get('conditionId')
        group_title = m.get('groupItemTitle', '')
        if not cond_id or not group_title:
            continue
            
        bucket = group_title.replace('°F', '').replace('F', '').replace('°', '').strip()
        print(f"Pobieranie cen dla: {bucket}")
        
        c_res = session.get(f"https://clob.polymarket.com/markets/{cond_id}")
        if c_res.status_code != 200: continue
        
        tokens = c_res.json().get('tokens', [])
        yes_token_id = next((t['token_id'] for t in tokens if t['outcome'].upper() == 'YES'), None)
        no_token_id = next((t['token_id'] for t in tokens if t['outcome'].upper() == 'NO'), None)
        
        if not yes_token_id or not no_token_id: continue
        
        y_res = session.get(f"https://clob.polymarket.com/prices-history?market={yes_token_id}&interval=max")
        y_hist = y_res.json().get('history', [])
        
        if not y_hist: continue
        
        df_y = pd.DataFrame(y_hist)
        df_y['timestamp'] = pd.to_datetime(df_y['t'], unit='s', utc=True)
        
        # Zapiszmy surowe dane
        for _, row in df_y.iterrows():
            all_raw_rows.append({
                'bucket': bucket,
                'raw_timestamp_utc': row['timestamp'],
                'raw_unix': row['t'],
                'price': row['p']
            })
            
        # Zróbmy resamplowanie zgodnie z kodem
        df_y_resampled = df_y.set_index('timestamp').resample('1h').ffill()
        df_y_resampled = df_y_resampled.reindex(full_index).ffill().bfill().reset_index()
        
        for _, row in df_y_resampled.iterrows():
            all_resampled_rows.append({
                'bucket': bucket,
                'snapshot_utc': row['timestamp'],
                'price': row['p']
            })
            
        time.sleep(0.2)
        
    df_raw = pd.DataFrame(all_raw_rows)
    df_res = pd.DataFrame(all_resampled_rows)
    
    # Sortowanie surowych
    df_raw = df_raw.sort_values(['bucket', 'raw_timestamp_utc'])
    df_res = df_res.sort_values(['bucket', 'snapshot_utc'])
    
    raw_path = os.path.join(os.path.dirname(__file__), 'miami_july10_raw.csv')
    res_path = os.path.join(os.path.dirname(__file__), 'miami_july10_resampled.csv')
    
    df_raw.to_csv(raw_path, index=False)
    df_res.to_csv(res_path, index=False)
    
    print(f"Zapisano surowe dane do {raw_path}")
    print(f"Zapisano zresamplowane dane do {res_path}")

if __name__ == '__main__':
    fetch_and_test()
