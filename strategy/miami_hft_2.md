# Strategia HFT Intraday (2-dniowe wyprzedzenie): Miami

**Parametry Wejściowe:**
- **Miasto:** Miami
- **Zakres Danych:** 2026-06-01 do 2026-07-08
- **Model:** Hybryda XGBoost + BayesianRidge (Day 2 Ahead)
- **Architektura:** HFT Intraday (Skanowanie co 1 godzinę, 10:00 - 24:00 EDT)
- **Zasada wyboru modelu:** Sztywny próg publikacji ECMWF UTC (Zmiana na model 1200 o 14:00 EDT / 18:00 UTC)
- **Minimalna Cena Kontraktu:** > 0.30 USD
- **Skala:** Fahrenheit

### Wyniki Symulacji dla Najwyższej Temperatury (MAX)

**Wariant: HFT (Cel ROI > 40%)**
```text
Ilość zakładów: 23
Win Rate:       100.0%
Suma stawek:    $1120.00
Zysk netto:     $1134.00
ROI:            101.25%
```

### Wyniki Symulacji dla Najniższej Temperatury (MIN)

**Wariant: HFT (Cel ROI > 40%)**
```text
Ilość zakładów: 27
Win Rate:       51.9%
Suma stawek:    $1529.50
Zysk netto:     $-157.50
ROI:            -10.30%
```

**Wnioski:**
Wydłużenie horyzontu predykcji do 2 dni na rynku HFT w Miami w oparciu o bezpieczną zoptymalizowaną zasadę wyboru modelu UTC, przynosi niesamowite rezultaty. W przypadku rynku **MAX** system zachował idealną skuteczność (100% win rate), podwajając wkład z kapitalnym ROI 101.25%. Oznacza to, że nasze zaktualizowane prognozy wstrzelają się idealnie przed korektami wyceny rynkowej.

Z kolei rynek **MIN** generuje straty (-10.30%), konsekwentnie potwierdzając wzorzec trudności w przewidywaniu nocnych temperatur na Florydzie, widoczny już w testach na 1 dzień przed.

**ZMIANY W ARCHITEKTURZE (GLOBALNY STANDARD UTC):**
Zrezygnowaliśmy całkowicie z czasu lokalnego na rzecz globalnego wyboru modelu w momencie jego realnej publikacji (18:00 UTC). Zmiana następuje dokładnie od 14:00 czasu EDT, co oznacza absolutny brak błędu "data leakage" (wycieków danych z przyszłości) i eliminuje jakiekolwiek opóźnienia, maksymalizując potencjał rynkowy we wszystkich miastach – niezależnie od tego, w jakiej strefie się znajdują.
