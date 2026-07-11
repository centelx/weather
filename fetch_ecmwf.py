import argparse
import requests

def fetch_ecmwf_forecast(lat, lon):
    url = "https://api.open-meteo.com/v1/ecmwf"
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": ["temperature_2m_max", "temperature_2m_min"],
        "timezone": "auto"
    }
    
    print(f"Pobieranie prognozy ECMWF dla współrzędnych: {lat}, {lon}...\n")
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        daily = data.get("daily", {})
        times = daily.get("time", [])
        max_temps = daily.get("temperature_2m_max", [])
        min_temps = daily.get("temperature_2m_min", [])
        
        if not times:
            print("Brak danych w odpowiedzi API.")
            return

        print("Prognoza temperatury (Model ECMWF - Open-Meteo):")
        print("-" * 50)
        
        # Ograniczamy do 3 dni (dzisiaj, jutro, pojutrze) jeśli są dostępne
        days_to_show = min(3, len(times))
        for i in range(days_to_show):
            date_str = times[i]
            max_t = max_temps[i]
            min_t = min_temps[i]
            
            if i == 0:
                day_label = "Dzisiaj"
            elif i == 1:
                day_label = "Jutro"
            elif i == 2:
                day_label = "Pojutrze"
            else:
                day_label = ""
                
            print(f"{date_str} ({day_label}):")
            print(f"  Najwyższa temperatura: {max_t} °C")
            print(f"  Najniższa temperatura: {min_t} °C")
            print("-" * 50)
            
    except requests.exceptions.RequestException as e:
        print(f"Błąd podczas połączenia z API: {e}")
    except Exception as e:
        print(f"Wystąpił nieoczekiwany błąd: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pobieranie prognozy temperatury z modelu ECMWF dla podanych współrzędnych.")
    parser.add_argument("latitude", type=float, help="Szerokość geograficzna (np. 52.23 dla Warszawy)")
    parser.add_argument("longitude", type=float, help="Długość geograficzna (np. 21.01 dla Warszawy)")
    
    args = parser.parse_args()
    fetch_ecmwf_forecast(args.latitude, args.longitude)
