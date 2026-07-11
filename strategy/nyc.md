# Dziennik Wyników Symulacji - Nowy Jork (NYC)

Ten plik służy do rejestrowania i śledzenia najlepszych parametrów naszej strategii dla rynków pogodowych na Polymarket.

## Weryfikacja Złotej Formuły - 2026-07-09

**Parametry Wejściowe:**
- **Miasto:** New York City (NYC)
- **Zakres Danych:** 2026-06-01 do 2026-07-08
- **Model:** Hybryda XGBoost + BayesianRidge (Time Isolated)
- **Run Modelu Pogodowego:** 1200 UTC / 0000 UTC
- **Minimalne Oczekiwane ROI (Edge):** > 10%
- **Minimalna Cena Kontraktu:** > 0.30 USD
- **Kara Spreadu:** +0.01 USD doliczana do wyceny rynkowej
- **Skala:** Fahrenheit (API rynkowe operuje na skali US)

### Wyniki Symulacji dla Najwyższej Temperatury (MAX)
```text
--- RAPORT Z BACKTESTU ---
Ilość zakładów: 24
Win Rate:       75.0%
Suma stawek:    $1454.00
Zysk netto:     $310.00
Końcowy portfel:$1310.00
ROI:            21.32%
```

### Wyniki Symulacji dla Najniższej Temperatury (MIN)
```text
--- RAPORT Z BACKTESTU ---
Ilość zakładów: 8
Win Rate:       75.0%
Suma stawek:    $472.00
Zysk netto:     $116.00
Końcowy portfel:$1116.00
ROI:            24.58%
```

**Wnioski:**
Zastosowanie Złotej Formuły w środowisku wschodniego wybrzeża USA wykazało niesamowitą stabilność i powtarzalność zysków (powyżej 20% dla obydwu typów rynku).
- Na rynku dziennym (MAX) model odnotowuje doskonały zysk operacyjny rzędu 21% z bardzo dobrą skutecznością 75%.
- Na rynku nocnym (MIN) rynek kreuje znacznie mniej okazji inwestycyjnych (tylko 8 "pewnych" zakładów spełniających twarde kryteria brzegowe). Jednakże, gdy te zakłady się pojawiają, ich trafność znowu wynosi potężne 75%, dając nam niemal 25% zwrotu!
Nowy Jork to rynek uniwersalny – możemy śmiało zostawić bota handlującego zarówno na temperaturach MAX jak i MIN.
