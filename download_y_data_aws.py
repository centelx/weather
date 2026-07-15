import requests
import datetime
import pandas as pd
import pytz
import os
import time

def fetch_weather_history(start_date, end_date):
    start_dt = datetime.datetime.strptime(start_date, "%Y%m%d")
    end_dt = datetime.datetime.strptime(end_date, "%Y%m%d")
    
    api_key = "e1f10a1e78da46f5b10a1e78da96f525"
    base_url = "https://api.weather.com/v1/location/KMIA:9:US/observations/historical.json"
    
    current_start = start_dt
    all_observations = []
    
    while current_start <= end_dt:
        current_end = current_start + datetime.timedelta(days=30)
        if current_end > end_dt:
            current_end = end_dt
            
        s_str = current_start.strftime("%Y%m%d")
        e_str = current_end.strftime("%Y%m%d")
        
        url = f"{base_url}?apiKey={api_key}&units=e&startDate={s_str}&endDate={e_str}"
        print(f"Pobieranie zakresu: {s_str} - {e_str}...")
        
        try:
            res = requests.get(url, timeout=15)
            if res.status_code == 200:
                data = res.json()
                obs = data.get('observations', [])
                all_observations.extend(obs)
            else:
                print(f"Błąd HTTP {res.status_code} dla {s_str}-{e_str}")
                print(res.text)
        except Exception as e:
            print(f"Błąd połączenia: {e}")
            
        current_start = current_end + datetime.timedelta(days=1)
        time.sleep(0.5) # Ochrona przed rate limit
        
    return all_observations

def process_and_save(observations, output_file):
    if not observations:
        print("Brak danych do zapisania.")
        return
        
    df = pd.DataFrame(observations)
    
    # Konwersja czasu na lokalny dla Miami
    tz = pytz.timezone("America/New_York")
    df['datetime'] = pd.to_datetime(df['valid_time_gmt'], unit='s', utc=True).dt.tz_convert(tz)
    df['date'] = df['datetime'].dt.date
    
    # Agregacja dzienna (maksymalna i minimalna temperatura w stopniach Celsjusza, bo units=m)
    daily = df.groupby('date').agg(
        temperature_max=('temp', 'max'),
        temperature_min=('temp', 'min'),
        temperature_mean=('temp', 'mean')
    ).reset_index()
    
    # Zaokrąglenie średniej do jednego miejsca po przecinku (max/min są z reguły całkowite w fahrenheitach)
    daily['temperature_mean'] = daily['temperature_mean'].round(1)
    
    # Filtr na daty pożądane przez użytkownika
    daily = daily[(daily['date'] >= datetime.date(2021, 4, 1)) & (daily['date'] <= datetime.date(2026, 7, 9))]
    
    # Sort chronologically just in case
    daily = daily.sort_values('date').reset_index(drop=True)
    
    daily.to_csv(output_file, index=False)
    print(f"Zapisano {len(daily)} dni do pliku: {output_file}")
    
if __name__ == "__main__":
    obs = fetch_weather_history("20210401", "20260709")
    os.makedirs("y_data_aws", exist_ok=True)
    
    out_file = "y_data_aws/y_miami.csv"
    process_and_save(obs, out_file)

