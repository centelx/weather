import os, re

dir_path = 'c:/Users/barto/Desktop/polymarket/weather/strategy'
results = []

for filename in os.listdir(dir_path):
    if filename.endswith('.md'):
        with open(os.path.join(dir_path, filename), 'r', encoding='utf-8') as f:
            content = f.read()
            
            # Find all occurrences of the backtest report (MAX and MIN)
            matches = re.finditer(r'Ilość zakładów:\s*(\d+).*?Suma stawek:\s*\$([\d\.]+).*?Zysk netto:\s*\$([-\d\.]+).*?ROI:\s*([-\d\.]+)%', content, re.DOTALL)
            
            for i, match in enumerate(matches):
                bets = int(match.group(1))
                stakes = float(match.group(2))
                profit = float(match.group(3))
                roi = float(match.group(4))
                
                if bets == 0:
                    continue
                    
                market_type = 'MAX' if i == 0 else 'MIN'
                
                results.append({
                    'city': filename.replace('.md', ''),
                    'market': market_type,
                    'bets': bets,
                    'stakes': stakes,
                    'profit': profit,
                    'roi': roi
                })

# Filter ROI > 15%
filtered = [r for r in results if r['roi'] > 15]

total_bets = sum(r['bets'] for r in filtered)
total_stakes = sum(r['stakes'] for r in filtered)
total_profit = sum(r['profit'] for r in filtered)
avg_roi = (total_profit / total_stakes) * 100 if total_stakes > 0 else 0

print('Filtered Cities:')
for r in filtered:
    print(f"{r['city']} ({r['market']}): ROI={r['roi']}%, Bets={r['bets']}, Stakes={r['stakes']}, Profit={r['profit']}")

print('\nSummary:')
print(f'Total Bets: {total_bets}')
print(f'Total Stakes: {total_stakes:.2f}')
print(f'Total Profit: {total_profit:.2f}')
print(f'Weighted Avg ROI: {avg_roi:.2f}%')
