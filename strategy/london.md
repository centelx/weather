# Dziennik Wyników Symulacji - Londyn

Ten plik służy do rejestrowania i śledzenia najlepszych parametrów naszej strategii dla rynków pogodowych na Polymarket.

## Weryfikacja Złotej Formuły - 2026-07-09

**Parametry Wejściowe:**
- **Miasto:** Londyn (UK)
- **Zakres Danych:** 2026-06-01 do 2026-07-08
- **Model:** Hybryda XGBoost + BayesianRidge (Time Isolated)
- **Run Modelu Pogodowego:** 1200 UTC / 0000 UTC
- **Minimalne Oczekiwane ROI (Edge):** > 10%
- **Minimalna Cena Kontraktu:** > 0.30 USD
- **Kara Spreadu:** +0.01 USD doliczana do wyceny rynkowej
- **Skala:** Celsjusz

### Wyniki Symulacji dla Najwyższej Temperatury (MAX)
```text
--- RAPORT Z BACKTESTU ---
Ilość zakładów: 33
Win Rate:       57.6%
Suma stawek:    $2031.50
Zysk netto:     $-169.50
Końcowy portfel:$830.50
ROI:            -8.34%
```

### Wyniki Symulacji dla Najniższej Temperatury (MIN)
```text
--- RAPORT Z BACKTESTU ---
Ilość zakładów: 43
Win Rate:       55.8%
Suma stawek:    $2194.00
Zysk netto:     $158.00
Końcowy portfel:$1158.00
ROI:            7.20%
```

**Wnioski:**
Zestawienie dla Londynu okazuje się być ogromnym rozczarowaniem i czyni go **najgorszym badanym rynkiem** ze wszystkich przeanalizowanych lokalizacji.
- Rynek dzienny (MAX) wykazuje całkowity brak wartości dodanej, skuteczność 57% owocuje stabilną stratą (-8.34%).
- Rynek nocny (MIN) w teorii wychodzi "na plus" inkasując +7.20% ROI (również przy 55% skuteczności - tu zadziałały taniej kupione pakiety). Jednakże przy takiej liczbie zakładów (43) to absolutnie mikroskopijna przewaga nad rynkiem, która przypomina rzut monetą obarczony ogromnym ryzykiem.
Londyn jest klimatycznie zbyt skomplikowany, by klasyczne modele wyciągały nad nim długofalową przewagę nad rynkiem graczy lokalnych, albo też społeczność graczy w Londynie jest potężna i niesamowicie efektywnie wycenia ryzyko na własnym podwórku.
Zalecenie: wyeliminować Londyn ze strategii inwestycyjnej.
