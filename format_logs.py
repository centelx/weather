import pandas as pd
import datetime

# Output file
out_file = 'backtest_verify.txt'

def process_log(filename, days_ahead):
    df = pd.read_csv(filename)
    results = []
    
    for _, row in df.iterrows():
        if not row['is_win']: continue
        
        target_date_str = row['date']
        target_date = datetime.datetime.strptime(target_date_str, '%Y-%m-%d').date()
        hour = row['hour']
        
        # Determine the run
        run_hour = '00:00 UTC' if hour < 14 else '12:00 UTC'
        run_date = target_date - datetime.timedelta(days=days_ahead)
        
        results.append(f"Data Rynku (Target): {target_date_str}\n"
                       f"Godzina postawienia zakładu (EDT): {hour}:00\n"
                       f"Typ zakładu: {row['type']} na przedział {row['bucket']} st. F\n"
                       f"Cena zakupu: {row['p_market']:.3f}\n"
                       f"Model Run (Źródło predykcji): {run_date.strftime('%Y-%m-%d')} o godzinie {run_hour}\n"
                       f"Typ prognozy: {days_ahead}-dniowa (Day {days_ahead})\n"
                       f"Zysk netto: ${row['profit']:.2f}\n"
                       f"---------------------------------------------------\n")
    return results

lines = []
lines.append("WERYFIKACJA ZAKŁADÓW - DALLAS (HFT, ROI > 40%)\n")
lines.append("===================================================\n\n")

# Day 1
day1_res = process_log('logs/intraday_logs/intraday_log_dallas_day1.csv', 1)
lines.append("### ZAKŁADY Z WYPRZEDZENIEM 1-DNIOWYM (DAY 1) ###\n")
lines.extend(day1_res)

# Day 2
day2_res = process_log('logs/intraday_logs/intraday_log_dallas_day2.csv', 2)
lines.append("\n### ZAKŁADY Z WYPRZEDZENIEM 2-DNIOWYM (DAY 2) ###\n")
lines.extend(day2_res)

with open(out_file, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print(f"Zapisano weryfikację do {out_file}")
