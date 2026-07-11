import os
import subprocess

cities = ["miami", "taipei", "shanghai", "london", "paris", "nyc", "seoul"]
results = []

for city in cities:
    print(f"\n==============================================")
    print(f"PROCESSING CITY: {city.upper()}")
    print(f"==============================================")
    
    # 1. Prepare data
    print("Preparing data...")
    subprocess.run(["python", "src/prepare_y_data.py", "--city", city], check=True)
    
    # 2. Train model
    print("Training model...")
    subprocess.run(["python", "src/train.py", "--city", city], check=True)
    
    # 3. Compare model and capture output
    print("Comparing models...")
    result = subprocess.run(["python", "src/compare_models.py", "--city", city, "--config", "day1_1200"], capture_output=True, text=True)
    print(result.stdout)
    results.append(f"--- {city.upper()} ---\n" + result.stdout + "\n")

with open("batch_results.txt", "w", encoding="utf-8") as f:
    f.writelines(results)

print("Batch training complete! Check batch_results.txt for full comparison.")
