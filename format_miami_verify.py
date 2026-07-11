import pandas as pd

def generate_verify_file():
    df = pd.read_csv("logs/intraday_logs/intraday_log_miami.csv")
    
    with open("miami_verify_max_day1.txt", "w", encoding="utf-8") as f:
        f.write("WERYFIKACJA ZAKŁADÓW - MIAMI (MAX TEMP, DAY 1 AHEAD)\n")
        f.write("="*60 + "\n\n")
        
        # Sortowanie po dacie rozliczenia i godzinie
        df = df.sort_values(by=['date', 'hour'])
        
        win_count = 0
        loss_count = 0
        
        for idx, row in df.iterrows():
            date = row['date']
            time = row['hour']
            bucket = row['bucket']
            price = row['cost']
            p_model = row['p_model']
            is_win = row['is_win']
            profit = row['profit']
            
            # W backteście "cost" to nasza stawka za akcję (zawsze na 'NIE', więc koszt to cena opcji NIE).
            # "profit" to czysty zysk lub strata. W intraday zysk brutto to 1.0, więc profit = 1.0 - cost (dla wygranej) lub -cost (dla przegranej).
            if is_win:
                result_str = f"WYGRANA (+${profit:.2f})"
                win_count += 1
            else:
                result_str = f"PRZEGRANA (${profit:.2f})"
                loss_count += 1
                
            f.write(f"Data Rozliczenia: {date}\n")
            f.write(f"Złożono zakład:   {time}:00 EDT\n")
            f.write(f"Rynek:            {bucket}\n")
            f.write(f"Postawiono:       NIE (Koszt opcji: ${price:.2f})\n")
            f.write(f"Model P(TAK):     {p_model:.2%}\n")
            f.write(f"Wynik:            {result_str}\n")
            f.write("-" * 40 + "\n")
            
        f.write(f"\nPodsumowanie: {win_count} Wygranych, {loss_count} Przegranych (Total: {win_count+loss_count})\n")

if __name__ == "__main__":
    generate_verify_file()
    print("Wygenerowano miami_verify_max_day1.txt")
