import requests
import json
import os

API_KEY = "141b38b06dmsh0db9300be505295p156efdjsn531fa791bdd7"
STATION_ID = "72202" # KMIA Miami International Airport

url = "https://meteostat.p.rapidapi.com/stations/daily"

querystring = {
    "station": STATION_ID,
    "start": "2026-06-01",
    "end": "2026-06-30",
    "units": "metric" # Pobierzmy w Celsjuszach
}

headers = {
    "x-rapidapi-key": API_KEY,
    "x-rapidapi-host": "meteostat.p.rapidapi.com"
}

print(f"Pobieranie danych dla stacji {STATION_ID} (KMIA)...")
response = requests.get(url, headers=headers, params=querystring)

if response.status_code == 200:
    data = response.json()
    if 'data' in data:
        print("\n=== WYNIKI DLA CZERWCA 2026 (Celsjusz) ===")
        print(f"{'Data':<15} {'Max Temp':<10} {'Avg Temp':<10} {'Min Temp':<10}")
        print("-" * 50)
        for row in data['data']:
            date = row.get('date', 'N/A')
            tmax = row.get('tmax')
            tavg = row.get('tavg')
            tmin = row.get('tmin')
            
            tmax_str = f"{tmax:.1f}" if tmax is not None else "N/A"
            tavg_str = f"{tavg:.1f}" if tavg is not None else "N/A"
            tmin_str = f"{tmin:.1f}" if tmin is not None else "N/A"
            
            print(f"{date:<15} {tmax_str:<10} {tavg_str:<10} {tmin_str:<10}")
        print("-" * 50)
        print("Zapytanie zakończone sukcesem.")
        
        # Zapis do pliku
        with open("meteostat_czerwiec_2026_kmia_celsius.txt", "w", encoding="utf-8") as f:
            f.write("=== WYNIKI DLA CZERWCA 2026 (Celsjusz) ===\n")
            f.write(f"{'Data':<15} {'Max Temp':<10} {'Avg Temp':<10} {'Min Temp':<10}\n")
            f.write("-" * 50 + "\n")
            for row in data['data']:
                date = row.get('date', 'N/A')
                tmax = row.get('tmax')
                tavg = row.get('tavg')
                tmin = row.get('tmin')
                tmax_str = f"{tmax:.1f}" if tmax is not None else "N/A"
                tavg_str = f"{tavg:.1f}" if tavg is not None else "N/A"
                tmin_str = f"{tmin:.1f}" if tmin is not None else "N/A"
                f.write(f"{date:<15} {tmax_str:<10} {tavg_str:<10} {tmin_str:<10}\n")
    else:
        print("Brak klucza 'data' w odpowiedzi JSON.")
        print("Odpowiedź API:", json.dumps(data, indent=2))
else:
    print(f"Błąd zapytania API. Kod statusu: {response.status_code}")
    print("Odpowiedź API:", response.text)
