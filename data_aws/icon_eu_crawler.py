import os
import requests
import datetime
import pandas as pd
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
import pytz
import bz2
import glob
import threading
import xarray as xr

try:
    import ecmwflibs
    d = os.path.dirname(ecmwflibs.__file__)
    if hasattr(os, 'add_dll_directory'):
        os.add_dll_directory(d)
    os.environ['PATH'] = d + os.pathsep + os.environ.get('PATH', '')
except ImportError:
    pass

class ICONEUCrawler:
    def __init__(self, city_name, lat, lon, timezone_str="UTC"):
        self.city_name = city_name
        self.target_lat = lat
        self.target_lon = lon
        self.target_lon_adj = lon if lon >= 0 else 360 + lon
        self.timezone_str = timezone_str
        self.base_url = "https://data.source.coop/dynamical/dwd-icon-grib/icon-eu/regular-lat-lon"
        
        self.target_vars = [
            "t_2m", "td_2m", "u_10m", "v_10m", "tot_prec", "clct", "pmsl"
        ]
        
        self.temp_dir = "temp_icon_eu_chunks"
        os.makedirs(self.temp_dir, exist_ok=True)
        self._cfgrib_lock = threading.Lock()

    def _process_single_hour(self, fcst, run_date_str, run_hour_str, YYYYMMDDHH):
        from requests.adapters import HTTPAdapter
        from requests.packages.urllib3.util.retry import Retry
        
        session = requests.Session()
        retry = Retry(connect=3, backoff_factor=0.5)
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        
        hour_record = {"fcst": fcst}
        
        for v_key in self.target_vars:
            fcst_str = f"{fcst:03d}"
            filename = f"icon-eu_europe_regular-lat-lon_single-level_{YYYYMMDDHH}_{fcst_str}_{v_key.upper()}.grib2.bz2"
            grib_url = f"{self.base_url}/{run_date_str}T{run_hour_str}/{v_key}/{filename}"
            
            chunk_file = os.path.join(self.temp_dir, f"{self.city_name}_{YYYYMMDDHH}_f{fcst_str}_{v_key}.grib2")
            
            try:
                print(f"Pobieranie URL: {grib_url}")
                res = session.get(grib_url, timeout=15)
                if res.status_code == 200:
                    print(f"Pobrano pomyślnie: {v_key}")
                    decompressed = bz2.decompress(res.content)
                    with open(chunk_file, 'wb') as f:
                        f.write(decompressed)
                
                with self._cfgrib_lock:
                    if os.path.exists(chunk_file):
                        ds = xr.open_dataset(chunk_file, engine='cfgrib')
                        x_var = list(ds.data_vars)[0]
                        val_matrix = ds[x_var]
                        lats = val_matrix.latitude.values
                        lons = val_matrix.longitude.values
                        
                        if lats.ndim == 1:
                            iy = np.argmin(np.abs(lats - self.target_lat))
                            ix = np.argmin(np.abs(lons - self.target_lon))
                            lat_s, lat_e = max(0, iy - 1), min(len(lats), iy + 2)
                            lon_s, lon_e = max(0, ix - 1), min(len(lons), ix + 2)
                            window = val_matrix.values[lat_s:lat_e, lon_s:lon_e]
                        else:
                            dist = (lats - self.target_lat)**2 + (lons - self.target_lon)**2
                            iy, ix = np.unravel_index(np.argmin(dist), dist.shape)
                            lat_s, lat_e = max(0, iy - 1), min(dist.shape[0], iy + 2)
                            lon_s, lon_e = max(0, ix - 1), min(dist.shape[1], ix + 2)
                            window = val_matrix.values[lat_s:lat_e, lon_s:lon_e]
                        
                        hour_record[f"{v_key}_mean"] = float(np.nanmean(window))
                        hour_record[f"{v_key}_max"] = float(np.nanmax(window))
                        hour_record[f"{v_key}_min"] = float(np.nanmin(window))
                        ds.close()
            except Exception as e:
                print(f"Błąd przy {v_key}: {e}")
            finally:
                for f in glob.glob(chunk_file + "*"):
                    try: os.remove(f)
                    except: pass
                        
        return hour_record

    def _fetch_single_run(self, target_date, local_start, local_end, run_date, run_hour_str):
        run_utc = pytz.utc.localize(datetime.datetime.combine(run_date, datetime.time(int(run_hour_str), 0)))
        fcst_start = max(0, int((local_start - run_utc).total_seconds() / 3600))
        fcst_end = int((local_end - run_utc).total_seconds() / 3600)
        
        if fcst_start > fcst_end or fcst_start > 78: 
            return None 
            
        run_date_str = run_date.strftime("%Y-%m-%d")
        YYYYMMDDHH = run_date.strftime("%Y%m%d") + run_hour_str
        print(f"[{self.city_name}] Pobieranie ICON-EU {YYYYMMDDHH} ({fcst_start}h - {fcst_end}h)")
        
        hourly_data = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(self._process_single_hour, fcst, run_date_str, run_hour_str, YYYYMMDDHH) for fcst in range(fcst_start, fcst_end + 1)]
            for future in as_completed(futures):
                res = future.result()
                if res and len(res) > 1:
                    hourly_data.append(res)
                    
        if not hourly_data: return None
        
        df = pd.DataFrame(hourly_data)
        res = {}
        suf = f"run_{run_hour_str}Z_icon"
        
        if "t_2m_mean" in df.columns:
            df["TMP_C"] = df["t_2m_mean"] - 273.15
            res[f'temperature_2m_max_{suf}'] = df["TMP_C"].max()
            res[f'temperature_2m_min_{suf}'] = df["TMP_C"].min()
            res[f'temperature_2m_mean_{suf}'] = df["TMP_C"].mean()
        if "clct_mean" in df.columns: res[f'cloud_cover_mean_{suf}'] = df["clct_mean"].mean()
        if "tot_prec_mean" in df.columns: res[f'precipitation_sum_{suf}'] = df["tot_prec_mean"].sum()
        if "u_10m_mean" in df.columns and "v_10m_mean" in df.columns:
            ws = np.sqrt(df["u_10m_mean"]**2 + df["v_10m_mean"]**2) * 3.6
            res[f'wind_speed_10m_max_{suf}'] = ws.max()
            res[f'wind_speed_10m_mean_{suf}'] = ws.mean()
        if "pmsl_mean" in df.columns: res[f'msl_pressure_mean_{suf}'] = df["pmsl_mean"].mean() / 100.0
        if "td_2m_mean" in df.columns: res[f'dew_point_2m_mean_{suf}'] = df["td_2m_mean"].mean() - 273.15

        return res

    def fetch_forecast_for_target_day(self, target_date_str):
        local_tz = pytz.timezone(self.timezone_str)
        target_date = pd.to_datetime(target_date_str).date()
        
        local_start = local_tz.localize(datetime.datetime.combine(target_date, datetime.time.min))
        local_end = local_tz.localize(datetime.datetime.combine(target_date, datetime.time.max))
        utc_start = local_start.astimezone(pytz.utc)
        utc_end = local_end.astimezone(pytz.utc)
        
        run_date = target_date - datetime.timedelta(days=1)
        runs = ["00", "06", "12", "18"]
        combined_result = {'Date': target_date}
        
        for run_hr in runs:
            res = self._fetch_single_run(target_date, utc_start, utc_end, run_date, run_hr)
            if res:
                combined_result.update(res)
                
        if len(combined_result) > 1:
            return combined_result
        return None
