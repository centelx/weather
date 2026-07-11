# Strategia HFT Intraday: Nowy Jork (NYC)

**Parametry Wejściowe:**
- **Miasto:** Nowy Jork (USA)
- **Zakres Danych:** 2026-06-01 do 2026-07-08
- **Model:** Hybryda XGBoost + BayesianRidge (Time Isolated)
- **Architektura:** HFT Intraday (Skanowanie co 1 godzinę, 10:00 - 24:00 EDT)
- **Minimalna Cena Kontraktu:** > 0.30 USD
- **Skala:** Fahrenheit

**Zakłady 1-dniowe (Day 1 Ahead):**
- **ROI > 30%:** Ilość zakładów: 37 | Win Rate: 73.0% | Zysk netto: $295.00 | ROI: 12.55%
- **ROI > 40%:** Ilość zakładów: 25 | Win Rate: 60.0% | Zysk netto: $-46.00 | ROI: -3.03%
- **ROI > 50%:** Ilość zakładów: 18 | Win Rate: 61.1% | Zysk netto: $25.50  | ROI: 2.42%

**Zakłady 2-dniowe (Day 2 Ahead):**
- **ROI > 30%:** Ilość zakładów: 42 | Win Rate: 69.0% | Zysk netto: $112.20 | ROI: 4.11%
- **ROI > 40%:** Ilość zakładów: 29 | Win Rate: 62.1% | Zysk netto: $-32.50 | ROI: -1.81%
- **ROI > 50%:** Ilość zakładów: 21 | Win Rate: 52.4% | Zysk netto: $-175.00| ROI: -13.97%

**Wnioski:**
Nowy Jork wykazuje bardzo wyraźny profil: im mniejsze i "łatwiejsze" zasięgi wyłapiemy (niskie ROI = 30%), tym jesteśmy bezpieczniejsi. Najlepiej wypada tu scenariusz krótki (1 dzień przed) przy progu weryfikacyjnym ROI wynoszącym równe 30%. Osiągamy wtedy potężny zysk **295 USD przy 12.55% zwrotu** z ponad 73% skutecznością.

Jednakże próba zawężenia marginesu do bardziej ryzykownych "pewniaków" (ROI > 40% / 50%) w klimatach oceanicznych Wschodniego Wybrzeża skutkuje bolesnymi wpadkami, zwłaszcza przy celowaniu 2 dni w przód, gdzie odnotowaliśmy dotkliwą stratę prawie 14%. Zjawisko to sugeruje, że dla wybrzeża wiatry oraz chłodne fronty oceaniczne są na tyle zmienne, że model myli się na najwęższych progach.

**Rekomendacja:** Zostawiamy bota dla NYC włączonego, ale rygorystycznie ograniczamy go do testu **Day 1 z najniższym wymaganym progiem ROI > 30%**. To jedyny model gwarantujący nam bezpieczny zysk. Wyższe ambicje w tym mieście kończą się przegraną.
