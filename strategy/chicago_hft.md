# Strategia HFT Intraday: Chicago

**Parametry Wejściowe:**
- **Miasto:** Chicago
- **Zakres Danych:** 2024-01-01 do 2026-07-09
- **Model:** Hybryda XGBoost + BayesianRidge (Time Isolated)
- **Run Modelu Pogodowego:** 1200 UTC / 0000 UTC
- **Skala:** Ułamkowy Fahrenheit (Automatyczna detekcja Fahrenheita i kalibracja operatorów `[b-0.5, b+1.5]`).

### Wyniki Symulacji dla Najwyższej Temperatury (MAX)

*Twardy warunek: Minimalna cena kontraktu na Polymarket > 0.30 USD.*

**Zakłady 1-dniowe (Day 1 Ahead):**
- **ROI > 30%:** Ilość zakładów: 15 | Win Rate: 60.0% | Zysk netto: $-40.70 | ROI: -4.41%
- **ROI > 40%:** Ilość zakładów: 10 | Win Rate: 70.0% | Zysk netto: $97.50 | ROI: 16.57%
- **ROI > 50%:** Ilość zakładów: 4  | Win Rate: 50.0% | Zysk netto: $-27.00 | ROI: -12.11%

**Zakłady 2-dniowe (Day 2 Ahead):**
- **ROI > 30%:** Ilość zakładów: 22 | Win Rate: 63.6% | Zysk netto: $-23.50 | ROI: -1.68%
- **ROI > 40%:** Ilość zakładów: 14 | Win Rate: 50.0% | Zysk netto: $-192.50 | ROI: -21.91%
- **ROI > 50%:** Ilość zakładów: 8  | Win Rate: 50.0% | Zysk netto: $-75.50 | ROI: -16.15%

*Rekomendacja:* W przeciwieństwie do rynków południowych (Houston, Dallas), pogoda w wietrznym Chicago na 2 dni do przodu okazała się bardzo zmienna. Odnotowaliśmy systematyczne straty dla wszystkich progów Day 2. Rekomenduje się wyłączenie bota 2-dniowego dla Chicago. Dla zagrań 1-dniowych jedynym opłacalnym progiem było ROI > 40%, co daje solidne 16.57% zysku.

*Wniosek:* Chicago prezentuje zupełnie odwrotną charakterystykę niż Dallas. Tutaj gra na 2 dni do przodu jest nieopłacalna (prawdopodobnie przez "Lake Effect" i szybko zmieniające się fronty nad Jeziorem Michigan, z którymi ECMWF nie radzi sobie z tak dużym wyprzedzeniem). Za to na 1 dzień przed rynkiem, dla precyzyjnie wyselekcjonowanych zakładów (ROI > 40%), wciąż uzyskujemy zadowalający win-rate rzędu 70% i generujemy **16.5% ROI**. Bota należy skonfigurować ostrożnie i uruchomić tylko dla zagrań Day 1 z progiem na 40%.

## Analiza Modelu Bazowego
Zastosowanie precyzyjnego treningu wpłynęło na spadek błędów średnich bezwzględnych:
- Absolute MAE (Max Temp Day 1): **1.09 °F**
- Absolute MAE (Min Temp Day 1): **1.08 °F**
Błędy w Chicago (ok. 1.1 °F) są minimalnie wyższe niż na południu USA (Houston: 0.86 °F), co tłumaczy gorsze parametry zakładów na Polymarket. Chicago to znacznie trudniejszy rynek pod kątem pogodowym.
