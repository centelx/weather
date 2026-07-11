# Strategia HFT Intraday: San Francisco

**Parametry Wejściowe:**
- **Miasto:** San Francisco (USA)
- **Zakres Danych:** 2024-01-01 do 2026-07-08
- **Model:** Hybryda XGBoost + BayesianRidge (Time Isolated)
- **Architektura:** HFT Intraday (Skanowanie co 1 godzinę, 10:00 - 24:00 EDT)
- **Minimalna Cena Kontraktu:** > 0.30 USD
- **Skala:** Fahrenheit

### Wyniki Symulacji dla Najwyższej Temperatury (MAX)

**Zakłady 1-dniowe (Day 1 Ahead):**
- **ROI > 30%:** Ilość zakładów: 19 | Win Rate: 52.6% | Zysk netto: $-238.00 | ROI: -19.54%
- **ROI > 40%:** Ilość zakładów: 11 | Win Rate: 36.4% | Zysk netto: $-270.00 | ROI: -40.79%
- **ROI > 50%:** Ilość zakładów: 4  | Win Rate: 25.0% | Zysk netto: $-105.00 | ROI: -51.72%

**Zakłady 2-dniowe (Day 2 Ahead):**
- **ROI > 30%:** Ilość zakładów: 20 | Win Rate: 60.0% | Zysk netto: $-115.50 | ROI: -8.94%
- **ROI > 40%:** Ilość zakładów: 12 | Win Rate: 58.3% | Zysk netto: $-43.00  | ROI: -5.90%
- **ROI > 50%:** Ilość zakładów: 4  | Win Rate: 25.0% | Zysk netto: $-116.50 | ROI: -54.31%

**Wnioski:**
San Francisco okazało się absolutnie najgorszym i najbardziej destrukcyjnym dla kapitału rynkiem w całym naszym zestawieniu. 
Mimo użycia zoptymalizowanych hybryd XGBoost i zasilenia modeli pełnym rocznym wektorem danych (921 dni połatanych na braki API), system nie jest w stanie pokonać rynku na Polymarket. Zanotowaliśmy katastrofalne spadki ROI rzędu od -6% aż po -54%. Przy najwyższych marginesach błędu (oczekiwane ROI > 50%) skuteczność modelu spada wręcz do 25%, co oznacza, że Polymarket dosłownie miażdży nasze przewidywania.

Powód jest brutalny i dobrze znany w meteorologii: specyficzny mikroklimat zatoki San Francisco i słynna mgła wdzierająca się z nad oceanu (zjawisko *Marine Layer*) powoduje, że standardowe pomiary modelu ECMWF mylą się o stopnie, za co bezlitośnie karzą nas rynki w zakładach ułamkowych Fahrenheita.

**Rekomendacja:** 
Kategoryczny zakaz handlu automatycznego na parametrach MAX dla San Francisco! Ten rynek to czarna dziura dla algorytmów opartych o standardowe zrzuty ECMWF z siatki globalnej. Wyrzucamy miasto z produkcyjnego potoku, zostaje tu wyłącznie do ewentualnych eksperymentów akademickich.
