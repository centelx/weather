# Dziennik Wyników Symulacji - Seul

Ten plik służy do rejestrowania i śledzenia najlepszych parametrów naszej strategii dla rynków pogodowych na Polymarket.

## Weryfikacja Złotej Formuły - 2026-07-09

**Parametry Wejściowe:**
- **Miasto:** Seul (Korea Południowa)
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
Ilość zakładów: 28
Win Rate:       57.1%
Suma stawek:    $1751.70
Zysk netto:     $-183.70
Końcowy portfel:$816.30
ROI:            -10.49%
```

### Wyniki Symulacji dla Najniższej Temperatury (MIN)
```text
--- RAPORT Z BACKTESTU ---
Ilość zakładów: 18
Win Rate:       77.8%
Suma stawek:    $958.50
Zysk netto:     $413.50
Końcowy portfel:$1413.50
ROI:            43.14%
```

**Wnioski:**
Seul to miasto pełne niespodzianek, które wykazuje biegunowo odwrotną charakterystykę w porównaniu do słonecznego Miami na Florydzie.
- Na rynku dziennym (MAX), model gubi się w rywalizacji z rynkiem. 57% skuteczności to stanowczo za mało by pokonać marżę na kontraktach (strata na poziomie 10%). Seul w dzień należy wpisać na czarną listę.
- Rynek nocny (MIN) to jednak **potężna maszyna do zarabiania pieniędzy**. Model przewiduje spadki temperatur z oszałamiającą skutecznością niemal 78%, co generuje niesamowite, bardzo stabilne **ROI na poziomie ponad 43%**. Nocne wahania klimatyczne w Korei Południowej są kompletnie źle wyceniane przez giełdę.
Strategia dla Seulu jest jasna: absolutny zakaz grania dniówek (MAX) i brutalne pompowanie kapitału w kontrakty nocne (MIN).
