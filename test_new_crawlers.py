import json
from aws_cloud_data.gfs_crawler import GFSCrawler
from aws_cloud_data.hrrr_crawler import HRRRCrawler
import pandas as pd

def main():
    print("Testing new GFS Crawler...")
    # Miami coordinates
    lat, lon = 25.85, -80.24
    tz = "America/New_York"
    
    gfs_crawler = GFSCrawler("miami", lat, lon, tz)
    gfs_res = gfs_crawler.fetch_forecast_for_target_day("2023-01-02")
    
    print("\nTesting new HRRR Crawler...")
    hrrr_crawler = HRRRCrawler("miami", lat, lon, tz)
    hrrr_res = hrrr_crawler.fetch_forecast_for_target_day("2023-01-02")
    
    final_res = {"GFS": gfs_res, "HRRR": hrrr_res}
    
    # Naprawa błędu serializacji JSON dla obiektów typu date i nan
    import math
    def clean_dict(d):
        if not d: return d
        for k, v in d.items():
            if hasattr(v, 'isoformat'):
                d[k] = v.isoformat()
            elif isinstance(v, float) and math.isnan(v):
                d[k] = None
        return d
        
    final_res["GFS"] = clean_dict(final_res["GFS"])
    final_res["HRRR"] = clean_dict(final_res["HRRR"])
    
    import os
    os.makedirs("scratch", exist_ok=True)
    with open("scratch/test_miami_aws.json", "w") as f:
        json.dump(final_res, f, indent=4)
        
    print("\n[ZAKOŃCZONO] Wyniki zapisane w scratch/test_miami_aws.json")

if __name__ == "__main__":
    main()
