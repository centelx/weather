# Dziennik Wyników Symulacji - Shanghai

Ten plik służy do rejestrowania i śledzenia najlepszych parametrów naszej strategii dla rynków pogodowych na Polymarket.

## Weryfikacja Złotej Formuły - 2026-07-09

**Parametry Wejściowe:**
- **Miasto:** Shanghai
- **Zakres Danych:** 2026-06-01 do 2026-07-08
- **Model:** Hybryda XGBoost + BayesianRidge (Time Isolated)
- **Run Modelu Pogodowego:** 1200 UTC
- **Minimalne Oczekiwane ROI (Edge):** > 10%
- **Minimalna Cena Kontraktu:** > 0.30 USD
- **Kara Spreadu:** +0.01 USD doliczana do wyceny rynkowej

### Wyniki Symulacji dla Najwyższej Temperatury (MAX)
```text
--- RAPORT Z BACKTESTU ---
Ilość zakładów: 48
Win Rate:       64.6%
Suma stawek:    $2980.90
Zysk netto:     $57.10
Końcowy portfel:$1057.10
ROI:            1.92%
```

### Wyniki Symulacji dla Najniższej Temperatury (MIN)
```text
--- RAPORT Z BACKTESTU ---
Ilość zakładów: 19
Win Rate:       52.6%
Suma stawek:    $1085.00
Zysk netto:     $-105.00
Końcowy portfel:$895.00
ROI:            -9.68%
```

**Wnioski:**
Weryfikacja na chińskim rynku ujawniła fascynujące zjawisko: nasza "Złota Formuła" (przynosząca krocie w Taipei), na rynku w Szanghaju wykazuje diametralnie różne zachowanie w zależności od typu prognozy. 
Model przewidujący temperatury maksymalne (MAX) radzi sobie całkiem nieźle, utrzymując się na plusie (prawie 2% ROI na trudnym, nowym rynku), podczas gdy przewidywanie temperatur minimalnych w nocy (MIN) przyniosło stratę rzędu 10%. To udowadnia, że rynek może drastycznie różnić się specyfiką wyceny (lub model ECMWF gorzej radzi sobie z nocnymi spadkami temperatur w rejonie delty Jangcy).
Zaleca się kategoryczne wyłączenie handlu na nocnych minimach dla Szanghaju.
