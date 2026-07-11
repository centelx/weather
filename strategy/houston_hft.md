# Strategia HFT Intraday: Houston

**Parametry Wejściowe:**
- **Miasto:** Houston (USA)
- **Zakres Danych:** 2024-01-01 do 2026-07-08
- **Model:** Hybryda XGBoost + BayesianRidge (Time Isolated)
- **Architektura:** HFT Intraday (Skanowanie co 1 godzinę)
- **Minimalna Cena Kontraktu:** > 0.30 USD
- **Skala:** Fahrenheit

### Wyniki Symulacji dla Najwyższej Temperatury (MAX)

**Zakłady 1-dniowe (Day 1 Ahead):**
- **ROI > 30%:** Ilość zakładów: 45 | Win Rate: 62.2% | Zysk netto: $38.50  | ROI: 1.42%
- **ROI > 40%:** Ilość zakładów: 33 | Win Rate: 57.6% | Zysk netto: $-30.50 | ROI: -1.61%
- **ROI > 50%:** Ilość zakładów: 28 | Win Rate: 60.7% | Zysk netto: $118.00 | ROI: 7.62%

**Zakłady 2-dniowe (Day 2 Ahead):**
- **ROI > 30%:** Ilość zakładów: 47 | Win Rate: 61.7% | Zysk netto: $-29.00 | ROI: -1.01%
- **ROI > 40%:** Ilość zakładów: 39 | Win Rate: 59.0% | Zysk netto: $-47.00 | ROI: -2.04%
- **ROI > 50%:** Ilość zakładów: 28 | Win Rate: 57.1% | Zysk netto: $15.50  | ROI: 1.00%

**Wnioski:**
Ostateczna weryfikacja na pełnym potoku (załatanie dziur w wektorach cech i zachowanie pełnej, 921-dniowej sezonowości) dla Houston sprowadza ten rynek z pozycji faworyta do miana stabilnego, aczkolwiek ciężkiego rynku letniego. 
Wcześniejsze optymistyczne wyniki (rzędu 30% ROI) okazały się anomalią spowodowaną rzadszym rynkiem w poprzednich, niekompletnych próbkach danych.

W rzeczywistości, wilgotność znad Zatoki Meksykańskiej mocno obciąża model dwudniowy (Day 2 Ahead) - tutaj system przeważnie notuje lekkie straty rzędu -1% do -2%, a przy najbardziej rygorystycznym progu wychodzi ledwo na zero (1% zysku).

Zupełnie inaczej wygląda **Day 1**, gdzie przy odpowiednio ostrym wymogu opłacalności (ROI > 50%) uderzamy z 60% skutecznością, osiągając zadowalające **7.62% ROI**. To jedyna bezpieczna droga dla tego specyficznego, dusznego miasta.

**Rekomendacja:** 
Houston zachowujemy w portfelu inwestycyjnym, ale nakładamy potężny kaganiec bezpieczeństwa. Uruchamiamy handlarza algorytmicznego **TYLKO** dla zakładów 1-dniowych (Day 1 Ahead) i **TYLKO** z wymogiem oczekiwanego zysku ROI > 50%. Wszelkie zakłady 2-dniowe są zbyt obarczone losowością wiatru morskiego w Teksasie.
