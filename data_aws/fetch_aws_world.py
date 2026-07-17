import argparse
import json
import os
import pandas as pd
from datetime import datetime, timedelta
import pytz
from gfs_crawler import GFSCrawler
from icon_global_crawler import ICONGlobalCrawler

def fetch_for_model(city, crawler, config, model_type):
    out_file = os.path.join("data_aws", "data", f"features_{city}_{model_type}_full.csv")
    
    start_date = pd.to_datetime("2023-03-01").date() # ICON-Global dostępny od marca 2023
    if os.path.exists(out_file):
        try:
            df_existing = pd.read_csv(out_file)
            if not df_existing.empty:
                last_date = pd.to_datetime(df_existing['Date'].max()).date()
                start_date = last_date + timedelta(days=1)
                print(f"Znaleziono istniejące dane {model_type.upper()}. Wznawianie od: {start_date}")
        except Exception as e:
            print(f"Błąd przy czytaniu {out_file}: {e}")
            
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
    parser = argparse.ArgumentParser(description="Pobieranie GFS i ICON-Global dla Reszty Świata")
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
        
    if config.get('secondary_model') != "ICON-GLOBAL":
        print(f"Pominięto {city}: ten skrypt służy tylko dla miast z secondary_model=ICON-GLOBAL.")
        return
        
    lat = float(config['lat'])
    lon = float(config['lon'])
    tz = config['timezone']
    
    os.makedirs(os.path.join("data_aws", "data"), exist_ok=True)
    
    # 1. GFS
    gfs_crawler = GFSCrawler(city, lat, lon, tz)
    # GFS ma dłuższą historię, używamy domyślnego start_date z GFSCrawler lub z nadpisanego
    # W fetch_for_model ustawiliśmy 2023-03-01. Ale dla GFS chcemy od 2021-04-01!
    # Napiszmy własną logikę tutaj.
    
    out_file_gfs = os.path.join("data_aws", "data", f"features_{city}_gfs_full.csv")
    start_date_gfs = pd.to_datetime("2021-04-01").date()
    if os.path.exists(out_file_gfs):
        df_g = pd.read_csv(out_file_gfs)
        if not df_g.empty: start_date_gfs = pd.to_datetime(df_g['Date'].max()).date() + timedelta(days=1)
    
    local_tz = pytz.timezone(tz)
    end_date = datetime.now(local_tz).date() - timedelta(days=1)
    
    for t in pd.date_range(start_date_gfs, end_date):
        d_str = t.strftime("%Y-%m-%d")
        print(f"\n[{city.upper()}] Przetwarzanie GFS na: {d_str}")
        df = gfs_crawler.fetch_forecast_for_target_day(d_str)
        if df:
            pd.DataFrame([df]).to_csv(out_file_gfs, mode='a', header=not os.path.exists(out_file_gfs), index=False)
    
    # 2. ICON-Global
    icon_crawler = ICONGlobalCrawler(city, lat, lon, tz)
    fetch_for_model(city, icon_crawler, config, "icon-global")

if __name__ == "__main__":
    main()
