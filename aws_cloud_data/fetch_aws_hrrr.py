import os
import requests
import datetime
import math
import subprocess
import sys

# Konfiguracja
CITY = "miami"
LAT, LON = 25.76, -80.19
TARGET_DATE = "20231231" # 31 grudnia 2023
RUN_HOUR = 0 # 00:00 UTC
BUCKET_URL = f"https://noaa-hrrr-bdp-pds.s3.amazonaws.com/hrrr.{TARGET_DATE}/conus"

def download_hrrr_chunk(date_str, run_hour, fcst_hour, output_file):
    run_str = f"{run_hour:02d}"
    fcst_str = f"{fcst_hour:02d}"
    
    idx_url = f"{BUCKET_URL}/hrrr.t{run_str}z.wrfsfcf{fcst_str}.grib2.idx"
    grib_url = f"{BUCKET_URL}/hrrr.t{run_str}z.wrfsfcf{fcst_str}.grib2"
    
    # 1. Pobieranie pliku index (.idx)
    res_idx = requests.get(idx_url)
    if res_idx.status_code != 200:
        print(f"Nie mona pobra indexu {idx_url}")
        return False
        
    lines = res_idx.text.split('\n')
    start_byte = None
    end_byte = None
    
    for i, line in enumerate(lines):
        if ":TMP:2 m above ground:" in line:
            parts = line.split(':')
            start_byte = int(parts[1])
            # Szukamy nastpnej linii, aby okreli end_byte
            if i + 1 < len(lines) and lines[i+1].strip():
                next_parts = lines[i+1].split(':')
                end_byte = int(next_parts[1]) - 1
            break
            
    if start_byte is None:
        print("Nie znaleziono zmiennej TMP na 2m")
        return False
        
    # 2. Pobieranie wycinka GRIB2 (Range Request)
    headers = {"Range": f"bytes={start_byte}-{end_byte if end_byte else ''}"}
    res_grib = requests.get(grib_url, headers=headers)
    
    if res_grib.status_code in (200, 206):
        with open(output_file, 'wb') as f:
            f.write(res_grib.content)
        return True
    else:
        print(f"Bd pobierania grib2: {res_grib.status_code}")
        return False

def extract_temperature(grib_file, target_lat, target_lon):
    try:
        import os
        try:
            import ecmwflibs
            d = os.path.dirname(ecmwflibs.__file__)
            if hasattr(os, 'add_dll_directory'):
                os.add_dll_directory(d)
            os.environ['PATH'] = d + os.pathsep + os.environ.get('PATH', '')
        except ImportError:
            pass

        import xarray as xr
        # Wczytujemy plik grib2 uzywajac silnika cfgrib
        ds = xr.open_dataset(grib_file, engine='cfgrib')
        
        # Wyodrbniamy zmienn TMP
        tmp = ds['t2m']
        
        # Obliczanie odlegosci na siatce konforemnej (Lambert) jest automatyczne
        # Dziki wektorowym koordynatom (latitude, longitude) w cfgrib
        lats = tmp.latitude.values
        lons = tmp.longitude.values
        
        # Poprawka dla formatu HRRR (dugoc od 0 do 360)
        target_lon_adj = target_lon if target_lon >= 0 else 360 + target_lon
        
        # Szukamy indeksu (x, y) z najblisz odlegoci Euclidean (proste i skuteczne na maych dystansach)
        import numpy as np
        dist = (lats - target_lat)**2 + (lons - target_lon_adj)**2
        min_idx = np.unravel_index(np.argmin(dist), dist.shape)
        
        val_k = tmp.values[min_idx]
        val_c = val_k - 273.15
        ds.close()
        return val_c
    except Exception as e:
        print(f"Bd podczas odczytu pliku GRIB: {e}")
        return None

def main():
    print(f"Rozpoczynam testowe pobieranie danych NOAA HRRR z chmury AWS dla Miami...")
    print(f"Run: 31 grudnia 2023 00:00 UTC (19:00 EST z 30 grudnia)")
    print(f"Zakres waznosci prognozy: 1 stycznia 2024 (00:00 - 24:00 czasu Miami)")
    
    temps = []
    
    # 31 Grudnia 00:00 UTC
    # 1 Stycznia 00:00 EST = 1 Stycznia 05:00 UTC -> 29 godzin do przodu (24 + 5 = 29)
    # 1 Stycznia 23:00 EST = 2 Stycznia 04:00 UTC -> 52 godziny do przodu (24 + 24 + 4)
    
    for fcst in range(29, 53): 
        out_grib = f"hrrr_tmp_00z_{fcst:02d}.grib2"
        print(f"Pobieranie T2M (fcst={fcst}h)... ", end="")
        
        if download_hrrr_chunk(TARGET_DATE, RUN_HOUR, fcst, out_grib):
            val_c = extract_temperature(out_grib, LAT, LON)
            if val_c is not None:
                temps.append(val_c)
                print(f"Znaleziono: {val_c:.2f} C")
            else:
                print("Bd analizy.")
        else:
            print("Bd pobierania.")
            
        # Sprztanie
        if os.path.exists(out_grib):
            os.remove(out_grib)
            
        if os.path.exists(out_grib + ".923a8.idx"):
            os.remove(out_grib + ".923a8.idx")
            
    if temps:
        max_t = max(temps)
        min_t = min(temps)
        print("\n--- WYNIKI (MIAMI - 2024-01-01 lokalnie z HRRR run 2023-12-31 19Z) ---")
        print(f"Spodziewana maksymalna temperatura: {max_t:.2f} C")
        print(f"Spodziewana minimalna temperatura:  {min_t:.2f} C")
        print("---------------------------------------------------------------------")
    else:
        print("Nie udao si wyodrbni temperatur.")

if __name__ == "__main__":
    main()
