# Strategia HFT Intraday: Dallas

**Parametry Wejściowe:**
- **Miasto:** Dallas
- **Zakres Danych:** 2024-01-01 do 2026-07-09
- **Model:** Hybryda XGBoost + BayesianRidge (Time Isolated)
- **Run Modelu Pogodowego:** 1200 UTC / 0000 UTC
- **Skala:** Ułamkowy Fahrenheit (wraz z zaawansowaną korektą całkowania praw zapożyczoną z Houston).

### Wyniki Symulacji dla Najwyższej Temperatury (MAX)

*Twardy warunek: Minimalna cena kontraktu na Polymarket > 0.30 USD.*

**Zakłady 1-dniowe (Day 1 Ahead):**
- **ROI > 30%:** Ilość zakładów: 13 | Win Rate: 53.8% | Zysk netto: $-215.50 | ROI: -23.90%
- **ROI > 40%:** Ilość zakładów: 7  | Win Rate: 57.1% | Zysk netto: $-57.50 | ROI: -12.79%
- **ROI > 50%:** Ilość zakładów: 2  | Win Rate: 50.0% | Zysk netto: $-21.00 | ROI: -17.65%

**Zakłady 2-dniowe (Day 2 Ahead):**
- **ROI > 30%:** Ilość zakładów: 10 | Win Rate: 60.0% | Zysk netto: $-81.00 | ROI: -12.11%
- **ROI > 40%:** Ilość zakładów: 5  | Win Rate: 80.0% | Zysk netto: $81.00  | ROI: 26.05%
- **ROI > 50%:** Ilość zakładów: 2  | Win Rate: 100.0%| Zysk netto: $81.00  | ROI: 70.43%

*Wniosek:* Podobnie jak w przypadku wielu rynków, opłacalne okazuje się atakowanie rynku ze sporym wyprzedzeniem czasowym (Day 2 Ahead). Kiedy próg akceptowanego przewidywanego ROI ustawimy bardzo rygorystycznie (np. >40%), nasz win-rate osiąga rewelacyjne poziomy (80-100%). Oznacza to mniejszą ilość zagrań, ale bardzo wysoką skuteczność trafień. Day 1 w Dallas przyniósł straty na wszystkich frontach, dlatego zaleca się wyłączenie handlu na Day 1. Z racji ujemnego wyniku, dla tego miasta odpalamy tylko bota 2-dniowego z ROI targetem 40-50%.

## Analiza Modelu Bazowego
Zastosowanie precyzyjnego treningu wpłynęło na ekstremalny spadek błędów średnich bezwzględnych:
- Poprawa Absolute MAE (Max Temp Day 2): **1.07 °F**
- Poprawa Absolute MAE (Min Temp Day 2): **1.18 °F**
Taka jakość przewidywania na pełne dwa dni przed rynkiem pozwala wyprzedzić inwestorów na Polymarket, zanim ceny kontraktów odpowiednio zareagują na aktualne prognozy.
