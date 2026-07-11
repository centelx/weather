import os
import subprocess

cities_info = {}
with open("sensor_coordinates.txt", "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line: continue
        parts = line.split(":")
        city = parts[0].strip()
        args = parts[1].strip()
        cities_info[city] = args

with open("final_report_0000.txt", "w", encoding="utf-8") as out:
    for city, args in cities_info.items():
        out.write(f"\n{'='*50}\n")
        out.write(f"CITY: {city.upper()}\n")
        out.write(f"{'='*50}\n\n")
        
        out.write(">>> BACKTEST (day1_0000 - Fahrenheit) <<<\n")
        print(f"Running backtest for {city}...")
        res_backtest = subprocess.run(["python", "src/backtest.py", "--city", city, "--config", "day1_0000", "-f"], capture_output=True, text=True)
        out.write(res_backtest.stdout)
        if res_backtest.stderr:
            out.write("ERRORS:\n" + res_backtest.stderr)
            
        out.write("\n>>> PREDICT (run_hour 0000 - Fahrenheit) <<<\n")
        print(f"Running predict for {city}...")
        
        # args looks like: --lat 40.76 --lon -73.86
        lat_lon = args.split()
        predict_cmd = ["python", "src/predict.py", "--city", city] + lat_lon + ["--run_hour", "0000", "-f"]
        res_predict = subprocess.run(predict_cmd, capture_output=True, text=True)
        out.write(res_predict.stdout)
        if res_predict.stderr:
            out.write("ERRORS:\n" + res_predict.stderr)
            
        out.write("\n")

print("All done! Results saved to final_report_0000.txt")
