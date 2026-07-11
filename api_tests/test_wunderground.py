import requests
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo

url = "https://api.weather.com/v1/location/KMIA:9:US/observations/historical.json?apiKey=e1f10a1e78da46f5b10a1e78da96f525&units=e&startDate=20260601&endDate=20260630"

print("Pobieranie danych z Wunderground API...")
response = requests.get(url)

if response.status_code == 200:
    data = response.json()
    observations = data.get("observations", [])
    
    if not observations:
        print("Brak obserwacji w odpowiedzi JSON.")
    else:
        # Konwersja do DataFrame
        df = pd.DataFrame(observations)
        
        # Konwersja czasu GMT na lokalny (Miami to America/New_York)
        miami_tz = ZoneInfo('America/New_York')
        df['datetime'] = pd.to_datetime(df['valid_time_gmt'], unit='s', utc=True).dt.tz_convert(miami_tz)
        df['date'] = df['datetime'].dt.date
        
        # Obliczenie statystyk dla każdego dnia
        daily_stats = df.groupby('date').agg(
            Max_Temp=('temp', 'max'),
            Min_Temp=('temp', 'min'),
            Avg_Temp=('temp', 'mean')
        ).reset_index()
        
        print("\n=== WYNIKI Z WUNDERGROUND API (Fahrenheit) ===")
        print(f"{'Data':<15} {'Max Temp':<10} {'Avg Temp':<10} {'Min Temp':<10}")
        print("-" * 50)
        
        output_lines = ["=== WYNIKI Z WUNDERGROUND API (Fahrenheit) ===\n",
                        f"{'Data':<15} {'Max Temp':<10} {'Avg Temp':<10} {'Min Temp':<10}\n",
                        "-" * 50 + "\n"]
        
        for _, row in daily_stats.iterrows():
            d = str(row['date'])
            tmax = f"{row['Max_Temp']:.1f}" if pd.notna(row['Max_Temp']) else "N/A"
            tavg = f"{row['Avg_Temp']:.1f}" if pd.notna(row['Avg_Temp']) else "N/A"
            tmin = f"{row['Min_Temp']:.1f}" if pd.notna(row['Min_Temp']) else "N/A"
            
            line = f"{d:<15} {tmax:<10} {tavg:<10} {tmin:<10}"
            print(line)
            output_lines.append(line + "\n")
            
        print("-" * 50)
        
        with open("wunderground_czerwiec_2026_kmia.txt", "w", encoding="utf-8") as f:
            f.writelines(output_lines)
            
        print("Zapisano wyniki do api_tests/wunderground_czerwiec_2026_kmia.txt")
else:
    print(f"Błąd zapytania. Status: {response.status_code}")
    print(response.text)
