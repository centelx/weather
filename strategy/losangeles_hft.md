# Strategia HFT Intraday: Los Angeles

**Parametry Wejściowe:**
- **Miasto:** Los Angeles (USA)
- **Zakres Danych:** 2024-01-01 do 2026-07-09
- **Model:** Hybryda XGBoost + BayesianRidge (Time Isolated)
- **Architektura:** HFT Intraday (Skanowanie co 1 godzinę)
- **Minimalna Cena Kontraktu:** > 0.30 USD
- **Skala:** Celsjusz (Zmapowane dla modelu, oryginalnie rynki w Fahrenheit)

### Wyniki Symulacji dla Najwyższej Temperatury (MAX)

**Zakłady 1-dniowe (Day 1 Ahead):**
- **ROI > 30%:** Ilość zakładów: 34 | Win Rate: 52.9% | Zysk netto: $-169.00 | ROI: -8.74%
- **ROI > 40%:** Ilość zakładów: 31 | Win Rate: 51.6% | Zysk netto: $-107.00 | ROI: -6.39%
- **ROI > 50%:** Ilość zakładów: 25 | Win Rate: 48.0% | Zysk netto: $-120.00 | ROI: -9.26%

**Zakłady 2-dniowe (Day 2 Ahead):**
- **ROI > 30%:** Ilość zakładów: 40 | Win Rate: 47.5% | Zysk netto: $-428.50 | ROI: -18.71%
- **ROI > 40%:** Ilość zakładów: 36 | Win Rate: 44.4% | Zysk netto: $-394.00 | ROI: -20.08%
- **ROI > 50%:** Ilość zakładów: 31 | Win Rate: 38.7% | Zysk netto: $-442.50 | ROI: -27.34%

**Wnioski:**
Zbudowaliśmy dla Los Angeles najmocniejszy i najczystszy zbiór od podstaw (1850 pobranych wektorów dla API), ale niestety po raz kolejny utwierdzamy się w przekonaniu, że kalifornijskie wybrzeże to absolutna pułapka dla modeli numerycznych. Podobnie jak w San Francisco, mamy tutaj do czynienia z tzw. "June Gloom" / "May Gray" – morską warstwą chmur (marine layer), która wędruje nad wybrzeżem i ulega wypaleniu w ciągu dnia w sposób niezwykle nieprzewidywalny. Globalne modele (ECMWF) kompletnie się na tym gubią, przypisując złe wagi anomaliom mikroklimatycznym.

Wyniki to bezwzględna "rzeź" kapitału. Nie ma tutaj znaczenia używany lewar (ROI). Żaden wariant nie ociera się nawet o break-even. Horyzont 48-godzinny (Day 2) niszczy od 18 do blisko 30 procent potrfela, podczas gdy zoptymalizowany Day 1 połyka od 6 do 9 procent. Nawet najostrzejszy filtr opłacalności wypluwa jedynie nietrafione sygnały fałszywe.

**Rekomendacja:** 
**ABSOLUTNY ZAKAZ HANDLU NA LOS ANGELES.** Model należy zdeprecjonować, a bota tradingowego odłączyć od stacji w Kalifornii. Rynek okazał się tak samo zdradliwy i niemożliwy do wymodelowania z dużą precyzją, jak przewidywania dla San Francisco. Trzymamy nasz kapitał wyłącznie na sprawdzonych generatorach gotówki, takich jak Londyn czy Seul!
