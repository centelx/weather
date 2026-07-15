import argparse
import json
import os
import pandas as pd
from datetime import datetime, timedelta
import pytz
from gfs_crawler import GFSCrawler
from hrrr_crawler import HRRRCrawler

def fetch_for_model(city, crawler, config, model_type):
    out_file = os.path.join("data_aws", "data", f"features_{city}_{model_type}_full.csv")
    
    # Determine start date
    start_date = pd.to_datetime("2021-04-01").date()
    if os.path.exists(out_file):
        try:
            df_existing = pd.read_csv(out_file)
            if not df_existing.empty:
                last_date = pd.to_datetime(df_existing['Date'].max()).date()
                start_date = last_date + timedelta(days=1)
                print(f"Znaleziono istniejące dane {model_type.upper()}. Wznawianie od: {start_date}")
        except Exception as e:
            print(f"Błąd przy czytaniu {out_file}: {e}")
            
    # Determine end date (yesterday local time)
    local_tz = pytz.timezone(config['timezone'])
    end_date = datetime.now(local_tz).date() - timedelta(days=1)
    
    dates_to_fetch = pd.date_range(start=start_date, end=end_date)
    
    if len(dates_to_fetch) == 0:
        print(f"Brak nowych dni do pobrania dla {model_type.upper()}.")
        return
        
    for t in dates_to_fetch:
        date_str = t.strftime("%Y-%m-%d")
        print(f"\n[{city.upper()}] Przetwarzanie {model_type.upper()} na: {date_str}")
        
        try:
            daily_features = crawler.fetch_forecast_for_target_day(date_str)
            if daily_features:
                df_day = pd.DataFrame([daily_features])
                file_exists = os.path.exists(out_file)
                df_day.to_csv(out_file, mode='a', header=not file_exists, index=False)
                print(f"[ZAPISANO] Sukces dla {date_str} ({model_type.upper()}).")
            else:
                print(f"[BRAK DANYCH] Brak pełnych danych {model_type.upper()} dla {date_str}.")
        except Exception as e:
            print(f"[BŁĄD] Nie udało się pobrać {model_type.upper()} dla {date_str}: {e}")

def main():
    parser = argparse.ArgumentParser(description="Pobieranie najnowszych brakujących dni z GFS (i ewentualnie HRRR)")
    parser.add_argument("--city", type=str, required=True, help="Slug miasta z cities_config.json")
    args = parser.parse_args()
    
    city = args.city
    
    with open("polymarket_all_data/cities_config.json", "r") as f:
        cities_config = json.load(f)
        
    if city not in cities_config:
        print(f"Błąd: Miasto '{city}' nie istnieje w cities_config.json")
        return
        
    config = cities_config[city]
    if not config.get('lat') or not config.get('lon'):
        print(f"Pominięto {city}: brak współrzędnych (lat/lon) w konfiguracji.")
        return
        
    lat = float(config['lat'])
    lon = float(config['lon'])
    tz = config['timezone']
    
    os.makedirs(os.path.join("data_aws", "data"), exist_ok=True)
    
    # 1. GFS (dla każdego miasta na świecie)
    gfs_crawler = GFSCrawler(city, lat, lon, tz)
    fetch_for_model(city, gfs_crawler, config, "gfs")
    
    # 2. HRRR (tylko dla USA)
    if config.get('model', '').upper() == 'USA':
        hrrr_crawler = HRRRCrawler(city, lat, lon, tz)
        fetch_for_model(city, hrrr_crawler, config, "hrrr")

if __name__ == "__main__":
    main()
