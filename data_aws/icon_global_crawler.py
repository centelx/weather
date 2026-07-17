import os
import datetime
import pandas as pd
import numpy as np
import pytz
import openmeteo_requests
import requests_cache
from retry_requests import retry

class ICONGlobalCrawler:
    def __init__(self, city_name, lat, lon, timezone_str="UTC"):
        self.city_name = city_name
        self.target_lat = lat
        self.target_lon = lon
        self.timezone_str = timezone_str
        
        cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
        self.retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
        self.openmeteo = openmeteo_requests.Client(session=self.retry_session)
        self.url = "https://archive-api.open-meteo.com/v1/archive"

    def _fetch_single_run(self, target_date, run_date, run_hour_str):
        # Open-Meteo pozwala wyciągnąć historyczną prognozę dla danego runu
        # symulujemy logikę pobierania GRIB poprzez odpytywanie API o ten sam interwał
        # Dla modelu globalnego pobierzemy z archive-api
        
        run_utc = datetime.datetime.combine(run_date, datetime.time(int(run_hour_str), 0))
        
        params = {
            "latitude": self.target_lat,
            "longitude": self.target_lon,
            "start_date": target_date.strftime("%Y-%m-%d"),
            "end_date": target_date.strftime("%Y-%m-%d"),
            "hourly": ["temperature_2m", "relative_humidity_2m", "dew_point_2m", "precipitation", "surface_pressure", "cloud_cover", "wind_speed_10m"],
            "models": "icon_global",
            "timezone": "UTC"
        }
        
        try:
            responses = self.openmeteo.weather_api(self.url, params=params)
            response = responses[0]
            hourly = response.Hourly()
            
            # Extract variables
            t2m = hourly.Variables(0).ValuesAsNumpy()
            rh2m = hourly.Variables(1).ValuesAsNumpy()
            d2m = hourly.Variables(2).ValuesAsNumpy()
            precip = hourly.Variables(3).ValuesAsNumpy()
            pmsl = hourly.Variables(4).ValuesAsNumpy()
            cc = hourly.Variables(5).ValuesAsNumpy()
            ws10 = hourly.Variables(6).ValuesAsNumpy()
            
            res = {}
            suf = f"run_{run_hour_str}Z_icon"
            
            if len(t2m) > 0 and not np.isnan(t2m).all():
                res[f'temperature_2m_max_{suf}'] = np.nanmax(t2m)
                res[f'temperature_2m_min_{suf}'] = np.nanmin(t2m)
                res[f'temperature_2m_mean_{suf}'] = np.nanmean(t2m)
            if len(rh2m) > 0 and not np.isnan(rh2m).all(): res[f'relative_humidity_2m_mean_{suf}'] = np.nanmean(rh2m)
            if len(d2m) > 0 and not np.isnan(d2m).all(): res[f'dew_point_2m_mean_{suf}'] = np.nanmean(d2m)
            if len(precip) > 0 and not np.isnan(precip).all(): res[f'precipitation_sum_{suf}'] = np.nansum(precip)
            if len(pmsl) > 0 and not np.isnan(pmsl).all(): res[f'msl_pressure_mean_{suf}'] = np.nanmean(pmsl)
            if len(cc) > 0 and not np.isnan(cc).all(): res[f'cloud_cover_mean_{suf}'] = np.nanmean(cc)
            if len(ws10) > 0 and not np.isnan(ws10).all():
                res[f'wind_speed_10m_max_{suf}'] = np.nanmax(ws10)
                res[f'wind_speed_10m_mean_{suf}'] = np.nanmean(ws10)
            
            return res if len(res) > 0 else None
            
        except Exception as e:
            return None

    def fetch_forecast_for_target_day(self, target_date_str):
        target_date = pd.to_datetime(target_date_str).date()
        run_date = target_date - datetime.timedelta(days=1)
        
        runs = ["00", "06", "12", "18"]
        combined_result = {'Date': target_date}
        
        print(f"[{self.city_name}] Pobieranie ICON-Global (Open-Meteo API) dla {target_date_str}")
        
        for run_hr in runs:
            res = self._fetch_single_run(target_date, run_date, run_hr)
            if res:
                combined_result.update(res)
                
        if len(combined_result) > 1:
            return combined_result
        return None
