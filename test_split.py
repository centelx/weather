import pandas as pd
from src.backtester import PolymarketBacktester
import os

city = "shanghai"
base_path = r'C:\Users\barto\Desktop\polymarket\weather'

df_preds = pd.read_csv(os.path.join(base_path, f'predictions_history_{city}.csv'))
df_prices = pd.read_csv(os.path.join(base_path, f'real_polymarket_prices_{city}.csv'))

df_merged = pd.merge(df_preds, df_prices, on=['target_date', 'type', 'bucket'], how='inner')

print("=== WYNIKI DLA SHANGHAI - MAX ===")
b_max = PolymarketBacktester(bankroll=1000)
b_max.run(df_merged[df_merged['type'] == 'MAX'])

print("\n=== WYNIKI DLA SHANGHAI - MIN ===")
b_min = PolymarketBacktester(bankroll=1000)
b_min.run(df_merged[df_merged['type'] == 'MIN'])
