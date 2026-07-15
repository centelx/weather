import os
import requests
import datetime
import pandas as pd
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
import pytz
import glob
import threading
import xarray as xr

# Zmienne środowiskowe dla eccodes na Windowsie
try:
    import ecmwflibs
    d = os.path.dirname(ecmwflibs.__file__)
    if hasattr(os, 'add_dll_directory'):
        os.add_dll_directory(d)
    os.environ['PATH'] = d + os.pathsep + os.environ.get('PATH', '')
except ImportError:
    pass

class HRRRCrawler:
    def __init__(self, city_name, lat, lon, timezone_str="America/New_York"):
        self.city_name = city_name
        self.target_lat = lat
        self.target_lon_adj = lon if lon >= 0 else 360 + lon
        self.timezone_str = timezone_str
        self.bucket_base = "https://noaa-hrrr-bdp-pds.s3.amazonaws.com"
        
        self.target_vars = [
            ":TMP:2 m above ground:",
            ":RH:2 m above ground:",
            ":TCDC:entire atmosphere:",
            ":UGRD:10 m above ground:",
            ":VGRD:10 m above ground:",
            ":APCP:surface:",
            ":MSLMA:mean sea level:",
            ":TMP:850 mb:",
            ":DPT:2 m above ground:",
            ":GFLUX:surface:",
            ":PWAT:entire atmosphere",
            ":DSWRF:surface:",
            ":HPBL:surface:"
        ]
        
        self.temp_dir = "temp_grib_chunks"
        os.makedirs(self.temp_dir, exist_ok=True)
        self._cfgrib_lock = threading.Lock()

    def _get_byte_ranges(self, session, idx_url):
        try:
            res = session.get(idx_url, timeout=15)
            if res.status_code != 200: return None
        except Exception: return None
        
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
                        end_byte = int(lines[i+1].split(':')[1]) - 1
                    
                    v_key = var.replace(":", "")
                    if "APCP" in v_key: v_key = "APCP"
                    elif "TMP" in v_key and "850" in v_key: v_key = "TMP850"
                    elif "TMP" in v_key: v_key = "TMP"
                    elif "RH" in v_key: v_key = "RH"
                    elif "TCDC" in v_key: v_key = "TCDC"
                    elif "UGRD" in v_key: v_key = "UGRD"
                    elif "VGRD" in v_key: v_key = "VGRD"
                    elif "MSLMA" in v_key: v_key = "PRMSL" # Map HRRR MSLMA to PRMSL
                    elif "DPT" in v_key: v_key = "DPT"
                    elif "GFLUX" in v_key: v_key = "GFLUX"
                    elif "PWAT" in v_key: v_key = "PWAT"
                    elif "DSWRF" in v_key: v_key = "DSWRF"
                    elif "HPBL" in v_key: v_key = "HPBL"
                    
                    byte_ranges[v_key] = (start_byte, end_byte)
                    break
        return byte_ranges

    def _process_single_hour(self, fcst, run_date_str, run_hour_str):
        from requests.adapters import HTTPAdapter
        from requests.packages.urllib3.util.retry import Retry
        
        session = requests.Session()
        retry = Retry(connect=3, backoff_factor=0.5)
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        
        idx_url = f"{self.bucket_base}/hrrr.{run_date_str}/conus/hrrr.t{run_hour_str}z.wrfsfcf{fcst:02d}.grib2.idx"
        grib_url = f"{self.bucket_base}/hrrr.{run_date_str}/conus/hrrr.t{run_hour_str}z.wrfsfcf{fcst:02d}.grib2"
        
        ranges = self._get_byte_ranges(session, idx_url)
        if not ranges: return None
            
        hour_record = {"fcst": fcst}
        
        for v_key, (s_byte, e_byte) in ranges.items():
            chunk_file = os.path.join(self.temp_dir, f"chunk_{self.city_name}_{run_date_str}_{run_hour_str}_f{fcst}_{v_key}.grib2")
            headers = {"Range": f"bytes={s_byte}-{e_byte if e_byte else ''}"}
            try:
                res = session.get(grib_url, headers=headers, timeout=10)
                if res.status_code in (200, 206):
                    with open(chunk_file, 'wb') as f:
                        f.write(res.content)
                
                with self._cfgrib_lock:
                    ds = xr.open_dataset(chunk_file, engine='cfgrib')
                    var_names_xr = {
                        "TMP": "t2m",
                        "TMP850": "t",
                        "RH": "r2",
                        "TCDC": "tcc",
                        "UGRD": "u10",
                        "VGRD": "v10",
                        "APCP": "tp",
                        "PRMSL": "mslma",
                        "DPT": "d2m",
                        "GFLUX": "gflux",
                        "PWAT": "pwat",
                        "DSWRF": "dswrf",
                        "HPBL": "hpbl"
                    }
                    
                    x_var = var_names_xr.get(v_key, list(ds.data_vars)[0])
                    if x_var not in ds: x_var = list(ds.data_vars)[0]
                        
                    val_matrix = ds[x_var]
                    lats = val_matrix.latitude.values
                    lons = val_matrix.longitude.values
                    
                    dist = (lats - self.target_lat)**2 + (lons - self.target_lon_adj)**2
                    iy, ix = np.unravel_index(np.argmin(dist), dist.shape)
                    lat_s, lat_e = max(0, iy - 1), min(dist.shape[0], iy + 2)
                    lon_s, lon_e = max(0, ix - 1), min(dist.shape[1], ix + 2)
                    window = val_matrix.values[lat_s:lat_e, lon_s:lon_e]
                    
                    hour_record[f"{v_key}_mean"] = float(np.nanmean(window))
                    hour_record[f"{v_key}_max"] = float(np.nanmax(window))
                    hour_record[f"{v_key}_min"] = float(np.nanmin(window))
                    ds.close()
            except Exception: pass
            finally:
                for f in glob.glob(chunk_file + "*"):
                    try: os.remove(f)
                    except: pass
                        
        # Usunięto mnożenie przez 3600, ponieważ APCP to zakumulowany opad w mm
            
        return hour_record

    def _fetch_single_run(self, target_date, local_start, local_end, run_date, run_hour_str):
        run_utc = pytz.utc.localize(datetime.datetime.combine(run_date, datetime.time(int(run_hour_str), 0)))
        fcst_start = max(0, int((local_start - run_utc).total_seconds() / 3600))
        fcst_end = int((local_end - run_utc).total_seconds() / 3600)
        
        # HRRR ma 48h prognozy tylko dla 00Z, 06Z, 12Z, 18Z
        if fcst_start > fcst_end or fcst_start > 48: 
            return None 
            
        run_date_str = run_date.strftime("%Y%m%d")
        print(f"[{self.city_name}] Pobieranie HRRR {run_date_str} {run_hour_str}Z ({fcst_start}h - {fcst_end}h)")
        
        hourly_data = []
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(self._process_single_hour, fcst, run_date_str, run_hour_str) for fcst in range(fcst_start, fcst_end + 1)]
            for future in as_completed(futures):
                res = future.result()
                if res and len(res) > 1:
                    hourly_data.append(res)
                    
        if not hourly_data: return None
        
        df = pd.DataFrame(hourly_data)
        res = {}
        suf = f"run_{run_hour_str}Z_hrrr"
        
        if "TMP_mean" in df.columns:
            df["TMP_C"] = df["TMP_mean"] - 273.15
            res[f'temperature_2m_max_{suf}'] = df["TMP_C"].max()
            res[f'temperature_2m_min_{suf}'] = df["TMP_C"].min()
            res[f'temperature_2m_mean_{suf}'] = df["TMP_C"].mean()
        if "RH_mean" in df.columns: res[f'relative_humidity_2m_mean_{suf}'] = df["RH_mean"].mean()
        if "TCDC_mean" in df.columns: res[f'cloud_cover_mean_{suf}'] = df["TCDC_mean"].mean()
        if "APCP_mean" in df.columns: res[f'precipitation_sum_{suf}'] = df["APCP_mean"].sum()
        if "UGRD_mean" in df.columns and "VGRD_mean" in df.columns:
            ws = np.sqrt(df["UGRD_mean"]**2 + df["VGRD_mean"]**2) * 3.6
            res[f'wind_speed_10m_max_{suf}'] = ws.max()
            res[f'wind_speed_10m_mean_{suf}'] = ws.mean()
            
        # Nowe zmienne
        if "TMP850_mean" in df.columns: res[f'temperature_850mb_mean_{suf}'] = df["TMP850_mean"].mean() - 273.15
        if "DPT_mean" in df.columns: res[f'dew_point_2m_mean_{suf}'] = df["DPT_mean"].mean() - 273.15
        if "PRMSL_mean" in df.columns: res[f'msl_pressure_mean_{suf}'] = df["PRMSL_mean"].mean() / 100.0 # hPa
        if "GFLUX_mean" in df.columns: res[f'ground_heat_flux_mean_{suf}'] = df["GFLUX_mean"].mean()
        if "PWAT_mean" in df.columns: res[f'precipitable_water_mean_{suf}'] = df["PWAT_mean"].mean()
        if "DSWRF_mean" in df.columns: res[f'downward_shortwave_mean_{suf}'] = df["DSWRF_mean"].mean()
        if "HPBL_mean" in df.columns: res[f'boundary_layer_height_mean_{suf}'] = df["HPBL_mean"].mean()

        return res

    def fetch_forecast_for_target_day(self, target_date_str):
        local_tz = pytz.timezone(self.timezone_str)
        target_date = pd.to_datetime(target_date_str).date()
        
        local_start = local_tz.localize(datetime.datetime.combine(target_date, datetime.time.min))
        local_end = local_tz.localize(datetime.datetime.combine(target_date, datetime.time.max))
        utc_start = local_start.astimezone(pytz.utc)
        utc_end = local_end.astimezone(pytz.utc)
        
        run_date = target_date - datetime.timedelta(days=1)
        
        # Pobieramy 4 duże runy HRRR (które mają prognozę do 48h)
        runs = ["00", "06", "12", "18"]
        combined_result = {'Date': target_date}
        
        for run_hr in runs:
            res = self._fetch_single_run(target_date, utc_start, utc_end, run_date, run_hr)
            if res:
                combined_result.update(res)
                
        if len(combined_result) > 1:
            return combined_result
        return None
