import os
import json
import requests
import pandas as pd
from datetime import datetime, timedelta
import time
import argparse

API_KEY = "e1f10a1e78da46f5b10a1e78da96f525"
GLOBAL_START_DATE = pd.to_datetime('2021-04-01').date()

def fetch_y_data_for_city(city_name, config, out_file):
    yesterday = (datetime.now() - timedelta(days=1)).date()
    start_date = GLOBAL_START_DATE
    
    # Mechanizm pamięci (wznawianie od ostatniego dnia)
    file_exists = os.path.exists(out_file)
    if file_exists:
        try:
            existing_df = pd.read_csv(out_file)
            if not existing_df.empty:
                last_date_str = existing_df['date'].max()
                last_date = pd.to_datetime(last_date_str).date()
                start_date = last_date + timedelta(days=1)
        except Exception as e:
            print(f"[{city_name.upper()}] Błąd odczytu {out_file}: {e}")
            
    if start_date > yesterday:
        print(f"[{city_name.upper()}] Dane Y są aktualne (do {yesterday}).")
        return
        
    print(f"[{city_name.upper()}] Pobieranie od {start_date} do {yesterday}...")
    station = config['wunderground_api']
    tz = config['timezone']
    
    current_start = start_date
    all_obs = []
    
    while current_start <= yesterday:
        current_end = current_start + timedelta(days=30)
        if current_end > yesterday:
            current_end = yesterday
            
        s_str = current_start.strftime("%Y%m%d")
        e_str = current_end.strftime("%Y%m%d")
        
        url = f"https://api.weather.com/v1/location/{station}/observations/historical.json?apiKey={API_KEY}&units=e&startDate={s_str}&endDate={e_str}"
        
        retries = 3
        while retries > 0:
            try:
                resp = requests.get(url, timeout=15)
                if resp.status_code == 200:
                    data = resp.json()
                    obs = data.get('observations', [])
                    all_obs.extend(obs)
                    print(f"  Pobrano miesiąc: {s_str} - {e_str} ({len(obs)} pomiarów)")
                    break
                else:
                    print(f"  Błąd HTTP {resp.status_code} dla {s_str}-{e_str}")
            except Exception as e:
                print(f"  Błąd połączenia: {e}")
                
            retries -= 1
            time.sleep(2)
            
        current_start = current_end + timedelta(days=1)
        time.sleep(0.5) # Ochrona przed zbanowaniem API
        
    if not all_obs:
        print(f"[{city_name.upper()}] Brak jakichkolwiek danych do zapisu.")
        return
        
    df = pd.DataFrame(all_obs)
    df = df.dropna(subset=['valid_time_gmt', 'temp'])
    
    # ---------------------------------------------------------
    # KLUCZOWY FIX: Rygorystyczna zmiana strefy z GMT na Local
    # ---------------------------------------------------------
    df['local_time'] = pd.to_datetime(df['valid_time_gmt'], unit='s', utc=True).dt.tz_convert(tz)
    df['date'] = df['local_time'].dt.date
    
    # Filtrujemy tylko pożądane dni (żeby nie ucięło w połowie przez dziwne przesunięcia miesiąca)
    df = df[(df['date'] >= start_date) & (df['date'] <= yesterday)]
    
    grouped = df.groupby('date')
    result = []
    for date, group in grouped:
        t_max = group['temp'].max()
        t_min = group['temp'].min()
        t_mean = group['temp'].mean()
        
        result.append({
            'date': date.strftime("%Y-%m-%d"),
            'temperature_max': float(t_max),
            'temperature_min': float(t_min),
            'temperature_mean': round(float(t_mean), 2)
        })
        
    if result:
        res_df = pd.DataFrame(result)
        # Zapis i dopisywanie do CSV w oryginalnych Fahrenheitach
        res_df.to_csv(out_file, mode='a', header=not file_exists, index=False)
        print(f"[{city_name.upper()}] Pomyślnie dopisano {len(res_df)} dni do pliku CSV.\n")
        file_exists = True

def main():
    parser = argparse.ArgumentParser(description="Masowe pobieranie danych Y (temperatury) z Wunderground")
    parser.add_argument("--city", type=str, default=None, help="Podaj nazwę miasta, aby pobrać tylko jedno")
    args = parser.parse_args()

    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "polymarket_all_data", "cities_config.json")
    
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            cities_config = json.load(f)
    except FileNotFoundError:
        print(f"Błąd: Nie znaleziono pliku config {config_path}")
        return

    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    os.makedirs(out_dir, exist_ok=True)

    cities_to_process = [args.city] if args.city else list(cities_config.keys())

    for city in cities_to_process:
        config = cities_config.get(city)
        if not config:
            continue
            
        if config.get("y_source") != "wunderground":
            continue
            
        station = config.get("wunderground_api", "")
        if not station:
            # Pomiń miasta bez uzupełnionego klucza lotniska
            continue
            
        out_file = os.path.join(out_dir, f"y_{city}.csv")
        fetch_y_data_for_city(city, config, out_file)

if __name__ == "__main__":
    main()
