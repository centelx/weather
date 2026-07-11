import os
import pandas as pd
from hrrr_crawler import HRRRCrawler

def main():
    city = "miami_precise"
    lat, lon = 25.79575604990449, -80.28567934789554
    timezone = "America/New_York"
    
    start_date = "2024-05-01"
    end_date = "2024-05-07"
    
    crawler = HRRRCrawler(city, lat, lon, timezone)
    
    dates_to_fetch = pd.date_range(start=start_date, end=end_date)
    results = []
    
    for t in dates_to_fetch:
        date_str = t.strftime("%Y-%m-%d")
        print(f"\n--- Przetwarzanie: {date_str} ---")
        
        daily_features = crawler.fetch_forecast_for_target_day(date_str)
        if daily_features:
            results.append(daily_features)
            print(f"Sukces dla {date_str}.")
        else:
            print(f"Brak danych dla {date_str}.")
            
    if results:
        df_features = pd.DataFrame(results)
        
        out_file = f"features_{city}_hrrr_test_may.csv"
        df_features.to_csv(out_file, index=False)
        print(f"\nUkończono! Zapisano plik: {out_file}")
    else:
        print("\nBrak jakichkolwiek pobranych danych.")

if __name__ == "__main__":
    main()
