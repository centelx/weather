# Strategia HFT Intraday: Denver

**Parametry Wejściowe:**
- **Miasto:** Denver (USA)
- **Zakres Danych:** 2026-06-01 do 2026-07-08
- **Model:** Hybryda XGBoost + BayesianRidge (Time Isolated)
- **Architektura:** HFT Intraday (Skanowanie co 1 godzinę, 10:00 - 24:00 EDT)
# Strategia HFT Intraday: Denver

**Parametry Wejściowe:**
- **Miasto:** Denver (USA)
- **Zakres Danych:** 2026-06-01 do 2026-07-08
- **Model:** Hybryda XGBoost + BayesianRidge (Time Isolated)
- **Architektura:** HFT Intraday (Skanowanie co 1 godzinę, 10:00 - 24:00 EDT)
- **Przełączanie Runów:** Sztywny próg publikacji ECMWF UTC (Zmiana na model 1200 o 14:00 EDT / 18:00 UTC)
- **Minimalna Cena Kontraktu:** > 0.30 USD (Odcięcie longshotów - **Kluczowy parametr dla Denver**)
- **Skala:** Fahrenheit

### Wyniki Symulacji dla Najwyższej Temperatury (MAX)

**Zakłady 1-dniowe (Day 1 Ahead):**
- **ROI > 30%:** Ilość zakładów: 40 | Win Rate: 65.0% | Zysk netto: $-4.15  | ROI: -0.16%
- **ROI > 40%:** Ilość zakładów: 29 | Win Rate: 62.1% | Zysk netto: $0.85   | ROI: 0.05%
- **ROI > 50%:** Ilość zakładów: 19 | Win Rate: 52.6% | Zysk netto: $-103.30 | ROI: -9.54%

**Zakłady 2-dniowe (Day 2 Ahead):**
- **ROI > 30%:** Ilość zakładów: 38 | Win Rate: 63.2% | Zysk netto: $-79.50 | ROI: -3.27%
- **ROI > 40%:** Ilość zakładów: 25 | Win Rate: 60.0% | Zysk netto: $-17.75 | ROI: -1.19%
- **ROI > 50%:** Ilość zakładów: 17 | Win Rate: 52.9% | Zysk netto: $-67.80 | ROI: -7.14%

**Wnioski:**
Zaskakujący obrót spraw. Po siłowym wrzuceniu do modelu wszystkich dni (imputacja sztucznie podtrzymująca brakujące 600 dni z historii), win-rate potężnie skoczył z ~45% do ponad 60-65%! Model dostał znacznie szerszy kontekst dla Denver i przestał generować katastrofalne straty (straty rzędu -100% zminimalizowały się do zaledwie -9%, a niektóre warianty jak Day 1 > 40% wyszły wręcz na minimalny, płaski plus: +0.05% ROI).
Okazuje się, że w tak wariackim klimacie górskim, model XGBoost woli dostać lekko zaszumione / syntetyczne dane, aby poznać układ sił za cały rok (zima, lato), niż uczyć się wyłącznie na 300 idealnych wiosennych / jesiennych rekordach wyjętych z kontekstu.

Mimo ogromnej poprawy skuteczności poprzez imputację danych, **rynek ten pozostaje niepraktyczny pod kątem dużego zysku.** Ryzyko wciąż jest zbyt wysokie, by stawiać tam realne pieniądze. Traktujemy Denver jako poligon doświadczalny – nie dodajemy go do portfela produkcyjnego.
