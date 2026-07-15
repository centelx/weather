import pandas as pd
import numpy as np
import os

try:
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

class Backtester:
    def __init__(self, df_preds, df_market, df_actuals, initial_bankroll=1000.0, edge_threshold=0.05, bet_size=10.0, fee_pct=0.0, min_price=0.30, max_price=0.99, side='ALL'):
        """
        Silnik backtestujący strategie na historycznych danych Polymarket.
        :param df_preds: DataFrame z naszymi predykcjami (target_date, forecast_horizon, type, bucket, model_probability)
        :param df_market: DataFrame z rynkowymi cenami Polymarket (target_date, forecast_horizon, type, bucket, market_probability)
        :param df_actuals: DataFrame z rzeczywistymi wynikami (target_date, actual_max, actual_min)
        :param initial_bankroll: Początkowy kapitał w USD
        :param edge_threshold: Minimalna przewaga (np. 0.05 = 5%), żeby otworzyć pozycję
        :param bet_size: Wielkość zakładu (USD)
        :param fee_pct: Prowizja/Slippage giełdy od wygranej (np. 0.02 to 2% fee)
        :param min_price: Minimalna cena kupna
        :param max_price: Maksymalna cena kupna
        :param side: Strona zakładu (YES, NO, ALL)
        """
        self.df_preds = df_preds
        self.df_market = df_market
        self.df_actuals = df_actuals
        
        self.initial_bankroll = initial_bankroll
        self.bankroll = initial_bankroll
        self.edge_threshold = edge_threshold
        self.bet_size = bet_size
        self.fee_pct = fee_pct
        self.min_price = min_price
        self.max_price = max_price
        self.side = side
        
        self.history = []
        self.equity_curve = []
        
    def run(self):
        print("--- Start Symulacji Backtestu ---")
        
        # Merge predykcji z cenami rynkowymi
        df = pd.merge(self.df_preds, self.df_market, on=['target_date', 'forecast_horizon', 'type', 'bucket'], how='inner')
        df['target_date'] = pd.to_datetime(df['target_date'])
        df = df.sort_values('target_date')
        
        unique_dates = df['target_date'].dt.date.unique()
        
        for date in unique_dates:
            day_trades = df[df['target_date'].dt.date == date]
            
            # Pobranie wyniku
            actual_row = self.df_actuals[self.df_actuals['target_date'] == str(date)]
            if actual_row.empty:
                continue
                
            actual_max = actual_row.iloc[0]['actual_max']
            actual_min = actual_row.iloc[0]['actual_min']
            
            daily_pnl = 0.0
            
            for _, trade in day_trades.iterrows():
                p_model_yes = trade['model_probability']
                p_market_yes_raw = trade['market_probability']
                
                if pd.isna(p_model_yes) or pd.isna(p_market_yes_raw):
                    continue
                    
                b_min, b_max = map(float, trade['bucket'].replace('C', '').replace('F', '').split('-'))
                if trade['type'] == 'MAX':
                    is_hit = (b_min <= actual_max <= b_max)
                else:
                    is_hit = (b_min <= actual_min <= b_max)
                
                # --- YES BET EVALUATION ---
                p_market_yes = min(0.99, p_market_yes_raw + 0.01) # dodajemy 0.01 dla pewności
                
                if self.min_price <= p_market_yes <= self.max_price:
                    cost_yes = p_market_yes * 100.0
                    shares = 100.0
                    net_payout_on_win = shares * (1.0 - self.fee_pct)
                    expected_revenue_yes = p_model_yes * net_payout_on_win
                    expected_profit_yes = expected_revenue_yes - cost_yes
                    expected_roi_yes = expected_profit_yes / cost_yes
                    
                    if expected_roi_yes > self.edge_threshold and self.side in ['ALL', 'YES']:
                        profit = net_payout_on_win - cost_yes if is_hit else -cost_yes
                        daily_pnl += profit
                        
                        self.history.append({
                            'date': date,
                            'type': trade['type'] + '_YES',
                            'horizon': trade['forecast_horizon'],
                            'bucket': trade['bucket'],
                            'p_model': p_model_yes,
                            'p_market': p_market_yes,
                            'exp_roi': expected_roi_yes,
                            'bet': cost_yes,
                            'profit': profit,
                            'is_win': is_hit
                        })
                        
                # --- NO BET EVALUATION ---
                if 'market_probability_no' in trade and pd.notna(trade['market_probability_no']):
                    p_market_no_raw = trade['market_probability_no']
                    p_market_no = min(0.99, p_market_no_raw + 0.01) # dodajemy 0.01 dla pewności
                    p_model_no = 1.0 - p_model_yes
                    
                    if self.min_price <= p_market_no <= self.max_price:
                        cost_no = p_market_no * 100.0
                        shares = 100.0
                        net_payout_on_win = shares * (1.0 - self.fee_pct)
                        expected_revenue_no = p_model_no * net_payout_on_win
                        expected_profit_no = expected_revenue_no - cost_no
                        expected_roi_no = expected_profit_no / cost_no
                        
                        if expected_roi_no > self.edge_threshold and self.side in ['ALL', 'NO']:
                            profit = net_payout_on_win - cost_no if not is_hit else -cost_no
                            daily_pnl += profit
                            
                            self.history.append({
                                'date': date,
                                'type': trade['type'] + '_NO',
                                'horizon': trade['forecast_horizon'],
                                'bucket': trade['bucket'],
                                'p_model': p_model_no,
                                'p_market': p_market_no,
                                'exp_roi': expected_roi_no,
                                'bet': cost_no,
                                'profit': profit,
                                'is_win': not is_hit
                            })
                    
            self.bankroll += daily_pnl
            self.equity_curve.append({'date': date, 'bankroll': self.bankroll})
            
    def generate_report(self, base_path):
        df_hist = pd.DataFrame(self.history)
        if df_hist.empty:
            print("Brak otwartych pozycji - przewaga nie przekroczyła progu.")
            return
            
        total_bets = len(df_hist)
        wins = df_hist['is_win'].sum()
        win_rate = wins / total_bets
        total_profit = df_hist['profit'].sum()
        total_cost = df_hist['bet'].sum()
        roi = total_profit / total_cost if total_cost > 0 else 0
        
        print(f"\n--- RAPORT Z BACKTESTU ---")
        print(f"Ilość zakładów: {total_bets}")
        print(f"Win Rate:       {win_rate*100:.1f}%")
        print(f"Suma stawek:    ${total_cost:.2f}")
        print(f"Zysk netto:     ${total_profit:.2f}")
        print(f"Końcowy portfel:${self.bankroll:.2f}")
        print(f"ROI:            {roi*100:.2f}%")
        
        # Zapis Equity Curve
        out_csv = os.path.join(base_path, 'equity_curve.csv')
        df_eq = pd.DataFrame(self.equity_curve)
        df_eq.to_csv(out_csv, index=False)
        print(f"Zapisano Equity Curve do {out_csv}")
        
        if MATPLOTLIB_AVAILABLE:
            try:
                plt.figure(figsize=(10,5))
                plt.plot(df_eq['date'], df_eq['bankroll'], marker='o', linestyle='-', color='b')
                plt.axhline(y=self.initial_bankroll, color='r', linestyle='--')
                plt.title("Zysk z portfela w czasie (Polymarket Simulation)")
                plt.xlabel("Data")
                plt.ylabel("Kapitał (USD)")
                plt.grid(True)
                out_png = os.path.join(base_path, 'equity_curve.png')
                plt.savefig(out_png)
                print(f"Zapisano wykres do {out_png}")
            except Exception as e:
                pass
        else:
            print("Matplotlib nie jest zainstalowany. Pomijam generowanie pliku .png.")
