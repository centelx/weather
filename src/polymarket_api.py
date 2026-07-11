import requests
import pandas as pd
import time
from datetime import datetime, timezone

class PolymarketAPI:
    """
    Klient do komunikacji z publicznym API Polymarket (Gamma & CLOB) 
    w celu pobierania danych rynkowych i historycznych świeczek cenowych.
    """
    
    GAMMA_URL = "https://gamma-api.polymarket.com"
    CLOB_URL = "https://clob.polymarket.com"
    
    def __init__(self):
        self.session = requests.Session()
        
    def get_event_by_slug(self, slug):
        """Pobiera dane wydarzenia (Event) na podstawie sluga URL."""
        url = f"{self.GAMMA_URL}/events"
        res = self.session.get(url, params={"slug": slug})
        if res.status_code == 200:
            data = res.json()
            if data and len(data) > 0:
                return data[0]
        return None
        
    def search_markets(self, limit=100, closed=True):
        """Pobiera najnowsze rynki z Gamma API."""
        url = f"{self.GAMMA_URL}/markets"
        res = self.session.get(url, params={"limit": limit, "closed": str(closed).lower()})
        if res.status_code == 200:
            return res.json()
        return []

    def get_price_history(self, token_id, interval="1h"):
        """
        Pobiera historię cen dla danego tokenu.
        Zwraca Pandas DataFrame z kolumnami [timestamp, price].
        """
        url = f"{self.CLOB_URL}/prices-history"
        params = {
            "market": token_id,
            "interval": interval
        }
        res = self.session.get(url, params=params)
        
        if res.status_code == 200:
            data = res.json()
            history = data.get('history', [])
            if not history:
                return pd.DataFrame()
                
            df = pd.DataFrame(history)
            df['t'] = pd.to_datetime(df['t'], unit='s', utc=True)
            df.rename(columns={'t': 'timestamp', 'p': 'price'}, inplace=True)
            df['price'] = df['price'].astype(float)
            return df
        return pd.DataFrame()

    def fetch_market_prices_at_time(self, token_id, target_date, hours_before=24):
        """
        Pomocnicza funkcja pobierająca cenę tokenu dokładnie X godzin przed target_date.
        Zakładamy, że rozliczenie jest na koniec dnia (UTC).
        """
        df_hist = self.get_price_history(token_id, interval="1h")
        if df_hist.empty:
            return None
            
        # Target date jako datetime (koniec dnia UTC)
        target_dt = datetime.strptime(f"{target_date} 23:59:59", "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        
        # Szukamy najświeższej ceny dostępnej przed zadanym momentem
        cutoff_dt = target_dt - pd.Timedelta(hours=hours_before)
        
        # Filtrujemy historię
        df_filtered = df_hist[df_hist['timestamp'] <= cutoff_dt]
        if df_filtered.empty:
            return None
            
        # Zwracamy ostatnią dostępną cenę przed cutoff_dt
        last_price_row = df_filtered.iloc[-1]
        return last_price_row['price']
