# Strategia HFT Intraday: Szanghaj (Chiny)

**Parametry Wejściowe:**
- **Miasto:** Szanghaj (Chiny)
- **Zakres Danych:** 2026-06-01 do 2026-07-08
- **Model:** Hybryda XGBoost + BayesianRidge (Time Isolated)
# Strategia HFT Intraday: Szanghaj (Chiny)

**Parametry Wejściowe:**
- **Miasto:** Szanghaj (Chiny)
- **Zakres Danych:** 2026-06-01 do 2026-07-08
- **Model:** Hybryda XGBoost + BayesianRidge (Time Isolated)
- **Architektura:** HFT Intraday (Skanowanie co 1 godzinę, 10:00 - 24:00 EDT)
- **Minimalna Cena Kontraktu:** > 0.30 USD
- **Skala:** Celsjusz

### Wyniki Symulacji dla Najwyższej Temperatury (MAX)

**Zakłady 1-dniowe (Day 1 Ahead):**
- **ROI > 30%:** Ilość zakładów: 55 | Win Rate: 67.3% | Zysk netto: $274.90 | ROI: 8.20%
- **ROI > 40%:** Ilość zakładów: 47 | Win Rate: 68.1% | Zysk netto: $445.75 | ROI: 16.57%
- **ROI > 50%:** Ilość zakładów: 35 | Win Rate: 57.1% | Zysk netto: $130.60 | ROI: 7.14%

**Zakłady 2-dniowe (Day 2 Ahead):**
- **ROI > 30%:** Ilość zakładów: 55 | Win Rate: 69.1% | Zysk netto: $212.85 | ROI: 6.06%
- **ROI > 40%:** Ilość zakładów: 44 | Win Rate: 63.6% | Zysk netto: $89.80  | ROI: 3.38%
- **ROI > 50%:** Ilość zakładów: 36 | Win Rate: 55.6% | Zysk netto: $27.10  | ROI: 1.40%

**Wnioski:**
Zaimplementowanie pełnego zestawu 921 dni (metodą Forward Fill łatającą braki od API) jeszcze mocniej ustabilizowało model dla Szanghaju! Tak jak przy Denver, dodanie szerszego, rocznego kontekstu podniosło Win-Rate do rekordowych na tym rynku poziomów (nawet **68-69% trafialności**). 

Najlepszym wariantem w ujęciu rocznym okazuje się teraz wejście **1 dzień wcześniej z wymogiem zwrotu 40%**. Generuje to absolutnie topowy wskaźnik **ROI wynoszący 16.57% z rewelacyjnym zyskiem netto równym $445.75 na zaledwie 47 starannie wyselekcjonowanych zakładach**.

Szanghaj, w przeciwieństwie do Denver, pozostaje modelem stabilnym we wszystkich wariantach czasowych, i zarabia na każdej opcji. Powinien być głównym rynkiem pod produkcyjny algorytm z wykorzystaniem ECMWF.
