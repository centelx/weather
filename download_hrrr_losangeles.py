import os
import pandas as pd
from aws_cloud_data.hrrr_crawler import HRRRCrawler

def main():
    city = "losangeles"
    lat, lon = 33.941872, -118.408849
    timezone = "America/Los_Angeles"
    
    start_date = "2022-01-01"
    end_date = "2026-07-09"
    
    crawler = HRRRCrawler(city, lat, lon, timezone)
    dates_to_fetch = pd.date_range(start=start_date, end=end_date)
    
    out_file = os.path.join("aws_datasets", f"features_{city}_hrrr_full.csv")
    
    # Check what was already downloaded
    downloaded_dates = set()
    if os.path.exists(out_file):
        try:
            df_existing = pd.read_csv(out_file)
            downloaded_dates = set(pd.to_datetime(df_existing['Date']).dt.strftime("%Y-%m-%d"))
            print(f"Znaleziono {len(downloaded_dates)} już pobranych dni. Wznawianie...")
        except Exception as e:
            print(f"Błąd przy czytaniu istniejącego pliku: {e}")
    
    for t in dates_to_fetch:
        date_str = t.strftime("%Y-%m-%d")
        
        if date_str in downloaded_dates:
            print(f"Pominięto {date_str} (już pobrano).")
            continue
            
        print(f"\n=========================================")
        print(f"Przetwarzanie: {date_str}")
        print(f"=========================================")
        
        daily_features = crawler.fetch_forecast_for_target_day(date_str)
        if daily_features:
            df_day = pd.DataFrame([daily_features])
            
            # Append to CSV
            file_exists = os.path.exists(out_file)
            df_day.to_csv(out_file, mode='a', header=not file_exists, index=False)
            print(f"[ZAPISANO] Sukces dla {date_str}. Dane bezpieczne na dysku.")
        else:
            print(f"[BRAK DANYCH] Nie znaleziono pełnych danych HRRR dla {date_str} na S3.")

if __name__ == "__main__":
    main()
