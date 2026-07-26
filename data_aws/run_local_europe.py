import json
import subprocess
import os

def main():
    # Pobieramy ścieżkę do katalogu głównego projektu (jeden poziom wyżej niż ten skrypt)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(current_dir)
    
    config_path = os.path.join(root_dir, "polymarket_all_data", "cities_config.json")
    
    with open(config_path, "r", encoding="utf-8") as f:
        cities_config = json.load(f)
        
    # Filtrowanie miast z Europy (ICON-EU) z zapisanymi współrzędnymi
    europe_cities = [
        city for city, info in cities_config.items()
        if info.get("secondary_model") == "ICON-EU" and info.get("lat") and info.get("lon")
    ]
    
    print(f"Znaleziono {len(europe_cities)} miast europejskich do pobrania:")
    for c in europe_cities:
        print(f" - {c}")
        
    print("\nRozpoczynam pobieranie (sekwencyjne)...")
    
    for idx, city in enumerate(europe_cities, 1):
        print(f"\n=======================================================")
        print(f"[{idx}/{len(europe_cities)}] Pobieranie danych dla: {city.upper()}")
        print(f"=======================================================")
        
        # Skrypt fetch_aws_europe.py znajduje się w tym samym katalogu (data_aws)
        script_path = os.path.join(current_dir, "fetch_aws_europe.py")
        cmd = ["python", "-u", script_path, "--city", city]
        
        try:
            # Ważne: uruchamiamy skrypt jako proces potomny, zachowując jako katalog roboczy (cwd) katalog główny
            subprocess.run(cmd, check=True, cwd=root_dir)
        except subprocess.CalledProcessError as e:
            print(f"\n[BŁĄD] Skrypt dla {city.upper()} zakończył się niepowodzeniem (kod błędu: {e.returncode})")
            continue

    print("\n[ZAKOŃCZONO] Pobieranie danych dla Europy dobiegło końca.")

if __name__ == "__main__":
    main()
