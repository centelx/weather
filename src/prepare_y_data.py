import os
import argparse
import pandas as pd
from datetime import datetime

MONTHS = {
    'styczen': 1, 'luty': 2, 'marzec': 3, 'kwiecien': 4,
    'maj': 5, 'czerwiec': 6, 'lipiec': 7, 'sierpien': 8,
    'wrzesien': 9, 'pazdziernik': 10, 'listopad': 11, 'grudzien': 12
}

def process_city_data(city, base_path):
    city_path = os.path.join(base_path, 'y_data', city)
    
    if not os.path.exists(city_path):
        print(f"Error: Directory {city_path} does not exist.")
        return
    
    all_data = []
    
    for filename in os.listdir(city_path):
        if not filename.endswith('.txt'):
            continue
            
        # Parse filename e.g. "czerwiec_2026.txt"
        name_parts = filename.replace('.txt', '').split('_')
        if len(name_parts) != 2:
            print(f"Warning: Skipping file {filename} - invalid format. Expected 'month_year.txt'")
            continue
            
        month_str, year_str = name_parts[0].lower(), name_parts[1]
        
        if month_str not in MONTHS:
            print(f"Warning: Unknown month '{month_str}' in file {filename}")
            continue
            
        month = MONTHS[month_str]
        try:
            year = int(year_str)
        except ValueError:
            print(f"Warning: Invalid year '{year_str}' in file {filename}")
            continue
            
        file_path = os.path.join(city_path, filename)
        
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        # Skip header if present. We look for "Max" or similar string, otherwise just assume first line is header.
        if not lines:
            continue
            
        start_idx = 1 if ('Max' in lines[0] or 'Avg' in lines[0] or 'Min' in lines[0]) else 0
        
        day = 1
        for line in lines[start_idx:]:
            line = line.strip()
            if not line:
                continue
                
            parts = line.split()
            if len(parts) < 3:
                print(f"Warning: Skipping invalid line in {filename}: {line}")
                continue
                
            try:
                max_t = float(parts[0])
                avg_t = float(parts[1])
                min_t = float(parts[2])
            except ValueError:
                print(f"Warning: Could not parse temperatures in line: {line}")
                continue
                
            try:
                date_obj = datetime(year, month, day).date()
            except ValueError as e:
                print(f"Warning: Invalid date {year}-{month}-{day} in {filename}. Stopping parsing for this file.")
                break
                
            # Data cleaning: fix erroneous 0s (often used as missing data in Wunderground)
            # A 0 is erroneous if it significantly deviates from expected value (Avg ≈ (Max + Min) / 2)
            # In Fahrenheit (avg_t > 40), 0 is always an error for our cities.
            is_fahrenheit_line = avg_t > 40.0
            
            if min_t == 0.0:
                expected_min = 2 * avg_t - max_t
                if is_fahrenheit_line or abs(0.0 - expected_min) > 3.0:
                    print(f"Fixing erroneous Min=0 on {year}-{month}-{day} in {city}. Changing to: {round(expected_min)}")
                    min_t = round(expected_min)
                    
            if max_t == 0.0:
                expected_max = 2 * avg_t - min_t
                if is_fahrenheit_line or abs(0.0 - expected_max) > 3.0:
                    print(f"Fixing erroneous Max=0 on {year}-{month}-{day} in {city}. Changing to: {round(expected_max)}")
                    max_t = round(expected_max)

            all_data.append({
                'Date': date_obj,
                'Max_Temp': max_t,
                'Avg_Temp': avg_t,
                'Min_Temp': min_t
            })
            day += 1

    if not all_data:
        print("No valid data found to process.")
        return
        
    df = pd.DataFrame(all_data)
    df = df.sort_values(by='Date')
    
    # Auto-detect Fahrenheit and convert to precise Celsius
    # If the mean Max_Temp is > 45, it is definitely Fahrenheit
    if df['Max_Temp'].mean() > 45:
        print(f"Wykryto dane w Fahrenheitach dla {city}! Automatyczna konwersja na precyzyjne stopnie Celsjusza...")
        df['Max_Temp'] = (df['Max_Temp'] - 32) / 1.8
        df['Avg_Temp'] = (df['Avg_Temp'] - 32) / 1.8
        df['Min_Temp'] = (df['Min_Temp'] - 32) / 1.8
    
    output_filename = f"merged_{city}.csv"
    output_path = os.path.join(city_path, output_filename)
    df.to_csv(output_path, index=False)
    
    print(f"Success! Processed {len(df)} rows.")
    print(f"Saved to: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process manual weather data for Polymarket predictions.")
    parser.add_argument("--city", required=True, help="Name of the city (folder name in y_data)")
    
    args = parser.parse_args()
    
    # Assume script is run from the project root or src folder
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Base project dir is the parent of src directory
    project_root = os.path.dirname(current_dir)
    
    process_city_data(args.city, project_root)
