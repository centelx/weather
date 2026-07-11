import os
import requests
import datetime
import pandas as pd
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
import pytz
import glob
import threading

# Zmienne środowiskowe dla eccodes na Windowsie
try:
    import ecmwflibs
    d = os.path.dirname(ecmwflibs.__file__)
    if hasattr(os, 'add_dll_directory'):
        os.add_dll_directory(d)
    os.environ['PATH'] = d + os.pathsep + os.environ.get('PATH', '')
except ImportError:
    pass

import xarray as xr

class HRRRCrawler:
    def __init__(self, city_name, lat, lon, timezone_str="America/New_York"):
        self.city_name = city_name
        self.target_lat = lat
        
        # Poprawka dla HRRR (długość geo od 0 do 360)
        self.target_lon_adj = lon if lon >= 0 else 360 + lon
        self.timezone_str = timezone_str
        self.bucket_base = "https://noaa-hrrr-bdp-pds.s3.amazonaws.com"
        
        self.target_vars = [
            ":TMP:2 m above ground:",
            ":RH:2 m above ground:",
            ":TCDC:entire atmosphere:",
            ":UGRD:10 m above ground:",
            ":VGRD:10 m above ground:",
            ":APCP:surface:"
        ]
        
        self.temp_dir = "temp_grib_chunks"
        os.makedirs(self.temp_dir, exist_ok=True)
        
        # Bezpiecznik C-Library
        self._cfgrib_lock = threading.Lock()

    def _get_byte_ranges(self, session, idx_url):
        try:
            res = session.get(idx_url, timeout=15)
            if res.status_code != 200:
                return None
        except Exception as e:
            print(f"Błąd HTTP dla {idx_url}: {e}")
            return None
        
        lines = res.text.split('\n')
        byte_ranges = {}
        
        for i, line in enumerate(lines):
            if not line.strip(): continue
            for var in self.target_vars:
                if var in line:
                    parts = line.split(':')
                    start_byte = int(parts[1])
                    
                    end_byte = None
                    if i + 1 < len(lines) and lines[i+1].strip():
                        next_parts = lines[i+1].split(':')
                        end_byte = int(next_parts[1]) - 1
                    
                    v_key = var.replace(":", "")
                    if "APCP" in v_key: v_key = "APCP"
                    elif "TMP" in v_key: v_key = "TMP"
                    elif "RH" in v_key: v_key = "RH"
                    elif "TCDC" in v_key: v_key = "TCDC"
                    elif "UGRD" in v_key: v_key = "UGRD"
                    elif "VGRD" in v_key: v_key = "VGRD"
                    
                    byte_ranges[v_key] = (start_byte, end_byte)
                    break
                    
        return byte_ranges

    def _process_single_hour(self, fcst, run_date_str):
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        
        session = requests.Session()
        retry = Retry(connect=3, backoff_factor=0.5)
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        
        idx_url = f"{self.bucket_base}/hrrr.{run_date_str}/conus/hrrr.t12z.wrfsfcf{fcst:02d}.grib2.idx"
        grib_url = f"{self.bucket_base}/hrrr.{run_date_str}/conus/hrrr.t12z.wrfsfcf{fcst:02d}.grib2"
        
        ranges = self._get_byte_ranges(session, idx_url)
        if not ranges:
            return None
            
        hour_record = {"fcst": fcst}
        
        for v_key, (s_byte, e_byte) in ranges.items():
            chunk_file = os.path.join(self.temp_dir, f"chunk_{self.city_name}_{run_date_str}_f{fcst}_{v_key}.grib2")
            headers = {"Range": f"bytes={s_byte}-{e_byte if e_byte else ''}"}
            try:
                res = session.get(grib_url, headers=headers, timeout=10)
                if res.status_code in (200, 206):
                    with open(chunk_file, 'wb') as f:
                        f.write(res.content)
                
                # Zabezpieczenie Thread-Safe przed błędem w C
                with self._cfgrib_lock:
                    ds = xr.open_dataset(chunk_file, engine='cfgrib')
                    
                    var_names_xr = {
                        "TMP": "t2m",
                        "RH": "r2",
                        "TCDC": "tcc",
                        "UGRD": "u10",
                        "VGRD": "v10",
                        "APCP": "tp"
                    }
                    
                    x_var = var_names_xr.get(v_key, list(ds.data_vars)[0])
                    if x_var not in ds:
                        x_var = list(ds.data_vars)[0]
                        
                    val_matrix = ds[x_var]
                    lats = val_matrix.latitude.values
                    lons = val_matrix.longitude.values
                    
                    dist = (lats - self.target_lat)**2 + (lons - self.target_lon_adj)**2
                    min_idx = np.unravel_index(np.argmin(dist), dist.shape)
                    iy, ix = min_idx
                    lat_s = max(0, iy - 1)
                    lat_e = min(dist.shape[0], iy + 2)
                    lon_s = max(0, ix - 1)
                    lon_e = min(dist.shape[1], ix + 2)
                    window = val_matrix.values[lat_s:lat_e, lon_s:lon_e]
                    
                    hour_record[f"{v_key}_mean"] = float(np.mean(window))
                    hour_record[f"{v_key}_max"] = float(np.max(window))
                    hour_record[f"{v_key}_min"] = float(np.min(window))
                    hour_record[f"{v_key}_std"] = float(np.std(window))
                    ds.close()
            except Exception as e:
                pass
            finally:
                # Agresywne usuwanie pliku .grib2 ORAZ wszystkich plików .idx (.grib2*)
                for f in glob.glob(chunk_file + "*"):
                    try:
                        os.remove(f)
                    except:
                        pass
                        
        return hour_record

    def fetch_forecast_for_target_day(self, target_date_str):
        local_tz = pytz.timezone(self.timezone_str)
        target_date = pd.to_datetime(target_date_str).date()
        
        local_start = local_tz.localize(datetime.datetime.combine(target_date, datetime.time.min))
        local_end = local_tz.localize(datetime.datetime.combine(target_date, datetime.time.max))
        
        utc_start = local_start.astimezone(pytz.utc)
        utc_end = local_end.astimezone(pytz.utc)
        
        run_date = target_date - datetime.timedelta(days=1)
        run_utc = pytz.utc.localize(datetime.datetime.combine(run_date, datetime.time(12, 0)))
        
        fcst_start = int((utc_start - run_utc).total_seconds() / 3600)
        fcst_end = int((utc_end - run_utc).total_seconds() / 3600)
        
        run_date_str = run_date.strftime("%Y%m%d")
        
        print(f"Fetching HRRR for {target_date_str} using run {run_date_str} 12Z. Forecast range: {fcst_start}h to {fcst_end}h")
        
        hourly_data = []
        
        # Gigabitowe pobieranie danych przy użyciu wątków!
        # Samo ładowanie GRIB jest zabezpieczone Lockiem.
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(self._process_single_hour, fcst, run_date_str) for fcst in range(fcst_start, fcst_end + 1)]
            for future in as_completed(futures):
                res = future.result()
                if res and len(res) > 1:
                    hourly_data.append(res)
            
        if not hourly_data:
            return None
            
        df = pd.DataFrame(hourly_data)
        
        result = {'Date': target_date}
        conf = "day1_1200"
        
        if "TMP_mean" in df.columns:
            df["TMP_mean_C"] = df["TMP_mean"] - 273.15
            df["TMP_max_C"] = df["TMP_max"] - 273.15
            df["TMP_min_C"] = df["TMP_min"] - 273.15
            result[f'temperature_2m_max_previous_{conf}_hrrr'] = df["TMP_max_C"].max()
            result[f'temperature_2m_min_previous_{conf}_hrrr'] = df["TMP_min_C"].min()
            result[f'temperature_2m_mean_previous_{conf}_hrrr'] = df["TMP_mean_C"].mean()
            result[f'temperature_2m_std_previous_{conf}_hrrr'] = df["TMP_std"].mean()
            
        if "RH_mean" in df.columns:
            result[f'relative_humidity_2m_mean_previous_{conf}_hrrr'] = df["RH_mean"].mean()
            result[f'relative_humidity_2m_std_previous_{conf}_hrrr'] = df["RH_std"].mean()
            
        if "TCDC_mean" in df.columns:
            result[f'cloud_cover_mean_previous_{conf}_hrrr'] = df["TCDC_mean"].mean()
            result[f'cloud_cover_std_previous_{conf}_hrrr'] = df["TCDC_std"].mean()
            
        if "APCP_mean" in df.columns:
            result[f'precipitation_sum_previous_{conf}_hrrr'] = df["APCP_mean"].sum()
            result[f'precipitation_max_previous_{conf}_hrrr'] = df["APCP_max"].max()
            result[f'precipitation_std_previous_{conf}_hrrr'] = df["APCP_std"].mean()
            
        if "UGRD_mean" in df.columns and "VGRD_mean" in df.columns:
            df["wind_speed_mean"] = np.sqrt(df["UGRD_mean"]**2 + df["VGRD_mean"]**2) * 3.6
            result[f'wind_speed_10m_max_previous_{conf}_hrrr'] = df["wind_speed_mean"].max()
            result[f'wind_speed_10m_mean_previous_{conf}_hrrr'] = df["wind_speed_mean"].mean()
            
        return result
