import argparse
import os
import requests
import pandas as pd
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from zoneinfo import ZoneInfo
import time

API_KEY = "e1f10a1e78da46f5b10a1e78da96f525"

def fetch_data_for_month(location, start_date, end_date):
    url = f"https://api.weather.com/v1/location/{location}/observations/historical.json?apiKey={API_KEY}&units=e&startDate={start_date}&endDate={end_date}"
    print(f"Pobieranie {start_date} do {end_date}...")
    response = requests.get(url)
    if response.status_code == 200:
        return response.json().get("observations", [])
    else:
        print(f"Błąd API {response.status_code}: {response.text}")
        return []

def main():
    parser = argparse.ArgumentParser(description="Pobiera historyczne dane (Fahrenheit) z Wunderground i zapisuje jako precyzyjne Celsjusze.")
    parser.add_argument("--city", type=str, required=True, help="Nazwa miasta (np. taipei)")
    parser.add_argument("--location", type=str, required=True, help="Format lokacji (np. RCSS:9:TW)")
    parser.add_argument("--start", type=str, required=True, help="Data początkowa YYYYMMDD")
    parser.add_argument("--end", type=str, required=True, help="Data końcowa YYYYMMDD")
    parser.add_argument("--out_dir", type=str, default="y_data_f", help="Katalog wyjściowy")
    parser.add_argument("--tz", type=str, default="Asia/Taipei", help="Strefa czasowa miasta (domyślnie Asia/Taipei)")
    
    args = parser.parse_args()
    
    start_dt = datetime.strptime(args.start, "%Y%m%d")
    end_dt = datetime.strptime(args.end, "%Y%m%d")
    
    all_observations = []
    
    current_dt = start_dt
    while current_dt <= end_dt:
        # Koniec miesiąca lub koniec ogólny
        next_month = current_dt + relativedelta(months=1)
        chunk_end = next_month - timedelta(days=1)
        if chunk_end > end_dt:
            chunk_end = end_dt
            
        start_str = current_dt.strftime("%Y%m%d")
        end_str = chunk_end.strftime("%Y%m%d")
        
        obs = fetch_data_for_month(args.location, start_str, end_str)
        all_observations.extend(obs)
        
        current_dt = next_month
        time.sleep(1) # Lekkie opóźnienie dla bezpieczeństwa
        
    if not all_observations:
        print("Nie pobrano żadnych obserwacji.")
        return
        
    df = pd.DataFrame(all_observations)
    
    # Konwersja czasu
    tz = ZoneInfo(args.tz)
    df['datetime'] = pd.to_datetime(df['valid_time_gmt'], unit='s', utc=True).dt.tz_convert(tz)
    df['date'] = df['datetime'].dt.date
    
    # Agregacja dzienna (w Fahrenheitach)
    daily_stats = df.groupby('date').agg(
        Max_Temp=('temp', 'max'),
        Min_Temp=('temp', 'min'),
        Avg_Temp=('temp', 'mean')
    ).reset_index()
    
    # Zastąpienie ew. zer lub braków przez proste średnie, chociaż z API nie powinno ich być w temp
    # Ale zróbmy to bezpiecznie
    for idx, row in daily_stats.iterrows():
        if pd.isna(row['Min_Temp']):
            daily_stats.at[idx, 'Min_Temp'] = 2 * row['Avg_Temp'] - row['Max_Temp']
        if pd.isna(row['Max_Temp']):
            daily_stats.at[idx, 'Max_Temp'] = 2 * row['Avg_Temp'] - row['Min_Temp']
            
    # Konwersja z dokładnych Fahrenheitów na dokładne Celsjusze (F -> C: (F - 32) / 1.8)
    daily_stats['Max_Temp'] = (daily_stats['Max_Temp'] - 32) / 1.8
    daily_stats['Avg_Temp'] = (daily_stats['Avg_Temp'] - 32) / 1.8
    daily_stats['Min_Temp'] = (daily_stats['Min_Temp'] - 32) / 1.8
    
    # Przygotowanie do zapisu (Date, Max_Temp, Avg_Temp, Min_Temp)
    out_df = daily_stats[['date', 'Max_Temp', 'Avg_Temp', 'Min_Temp']].rename(columns={'date': 'Date'})
    out_df['Date'] = pd.to_datetime(out_df['Date'])
    out_df = out_df.sort_values(by='Date')
    
    # Tworzenie folderów
    city_dir = os.path.join(args.out_dir, args.city)
    os.makedirs(city_dir, exist_ok=True)
    
    out_path = os.path.join(city_dir, f"merged_{args.city}.csv")
    out_df.to_csv(out_path, index=False)
    
    print(f"\nSukces! Przetworzono i zapisano {len(out_df)} dni do {out_path}.")
    print("Przykładowe dane (już w precyzyjnych Celsjuszach):")
    print(out_df.head())

if __name__ == "__main__":
    main()
