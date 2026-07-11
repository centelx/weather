# Dziennik Wyników Symulacji - Miami

Ten plik służy do rejestrowania i śledzenia najlepszych parametrów naszej strategii dla rynków pogodowych na Polymarket.

## Weryfikacja Złotej Formuły - 2026-07-09

**Parametry Wejściowe:**
- **Miasto:** Miami
- **Zakres Danych:** 2026-06-01 do 2026-07-08
- **Model:** Hybryda XGBoost + BayesianRidge (Time Isolated)
- **Run Modelu Pogodowego:** 1200 UTC / 0000 UTC
- **Minimalne Oczekiwane ROI (Edge):** > 10%
- **Minimalna Cena Kontraktu:** > 0.30 USD
- **Kara Spreadu:** +0.01 USD doliczana do wyceny rynkowej
- **Skala:** Fahrenheit (API rynkowe i modelowane operuje na lokalnej skali US)

### Wyniki Symulacji dla Najwyższej Temperatury (MAX)
```text
--- RAPORT Z BACKTESTU ---
Ilość zakładów: 28
Win Rate:       89.3%
Suma stawek:    $1360.50
Zysk netto:     $1089.50
Końcowy portfel:$2089.50
ROI:            80.08%
```

### Wyniki Symulacji dla Najniższej Temperatury (MIN)
```text
--- RAPORT Z BACKTESTU ---
Ilość zakładów: 32
Win Rate:       65.6%
Suma stawek:    $1924.00
Zysk netto:     $134.00
Końcowy portfel:$1134.00
ROI:            6.96%
```

**Wnioski:**
Zastosowanie rygorystycznych barier zapobiegających wyciekowi danych (Data Leakage) w połączeniu z podziałem na MAX i MIN przyniosło absolutnie oszałamiające rezultaty na rynku w Miami.
- Model trafia przewidywania fal upałów w Miami z niebywałą skutecznością rzędu blisko **90%**. Pozwoliło to na wygenerowanie kolosalnego **ROI rzędu 80%** z zaledwie 28 starannie wyselekcjonowanych zakładów z najwyższym priorytetem.
- Ekstrema nocne (MIN) zachowują stabilną rentowność (~7% ROI), potwierdzając, że wyceny nocne w Miami są efektywniejsze niż w Szanghaju, lecz wciąż nie dorównują predykcji upałów dziennych.
Miami stanowi żyłę złota na dziennych upałach w skali Fahrenheita.
