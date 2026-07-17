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

us_cities = ["miami", "nyc"]

for run_hour in ["1200", "0000"]:
    report_name = f"final_report_{run_hour}.txt"
    if run_hour == "1200":
        report_name = "final_report.txt"
        
    with open(report_name, "w", encoding="utf-8") as out:
        for city, args in cities_info.items():
            unit_str = "Fahrenheit" if city in us_cities else "Celsius"
            f_flag = ["-f"] if city in us_cities else []
            
            out.write(f"\n{'='*50}\n")
            out.write(f"CITY: {city.upper()}\n")
            out.write(f"{'='*50}\n\n")
            
            out.write(f">>> BACKTEST (day1_{run_hour} - {unit_str}) <<<\n")
            print(f"Running backtest for {city} (run {run_hour})...")
            
            backtest_cmd = ["python", "src/backtest.py", "--city", city, "--config", f"day1_{run_hour}"] + f_flag
            res_backtest = subprocess.run(backtest_cmd, capture_output=True, text=True)
            out.write(res_backtest.stdout)
            if res_backtest.stderr:
                out.write("ERRORS:\n" + res_backtest.stderr)
                
            out.write(f"\n>>> PREDICT (run_hour {run_hour} - {unit_str}) <<<\n")
            print(f"Running predict for {city} (run {run_hour})...")
            
            lat_lon = args.split()
            predict_cmd = ["python", "src/predict.py", "--city", city] + lat_lon + ["--run_hour", run_hour] + f_flag
            res_predict = subprocess.run(predict_cmd, capture_output=True, text=True)
            out.write(res_predict.stdout)
            if res_predict.stderr:
                out.write("ERRORS:\n" + res_predict.stderr)
                
            out.write("\n")

print("All done! Results saved to final_report.txt and final_report_0000.txt")
