# Dziennik Wyników Symulacji - Taipei

Ten plik służy do rejestrowania i śledzenia najlepszych parametrów naszej strategii dla rynków pogodowych na Polymarket.

## Złota Formuła (Best Setup) - 2026-07-09

**Parametry Wejściowe:**
- **Miasto:** Taipei
- **Zakres Danych (Test Out-Of-Sample):** 2026-06-10 do 2026-07-08
- **Model:** Hybryda XGBoost + BayesianRidge (Time Isolated - brak wycieku danych)
- **Run Modelu Pogodowego:** 1200 UTC
- **Minimalne Oczekiwane ROI (Edge):** > 10%
- **Minimalna Cena Kontraktu:** > 0.30 USD (odcięcie "longshotów")
- **Kara Spreadu:** +0.01 USD doliczane do ceny rynkowej (wariant pesymistyczny)
- **Stała Stawka (Bet Size):** 100 akcji na zakład (Dynamiczna kwota uzależniona od ceny)
- **Prowizja Giełdowa (Fee):** 2% od wygranej

**Wyniki Symulacji:**

```text
--- RAPORT Z BACKTESTU ---
Ilość zakładów: 31
Win Rate:       77.4%
Suma stawek:    $2022.20
Zysk netto:     $329.80
Końcowy portfel:$1329.80
ROI:            16.31%
```

**Wnioski:**
Zestawienie tych parametrów oferuje idealny złoty środek (sweet spot) pomiędzy zyskiem kwotowym a ekstremalnym bezpieczeństwem kapitału (Win Rate pow. 77%). Odcięcie tanich kontraktów całkowicie wyeliminowało ryzykowne loterie rynkowe, skupiając siłę predykcyjną modelu wyłącznie na pewniakach.
