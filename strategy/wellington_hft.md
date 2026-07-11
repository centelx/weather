# Strategia HFT Intraday: Wellington

**Parametry Wejściowe:**
- **Miasto:** Wellington (Nowa Zelandia)
- **Zakres Danych:** 2024-01-01 do 2026-07-08
- **Model:** Hybryda XGBoost + BayesianRidge (Time Isolated)
- **Architektura:** HFT Intraday (Skanowanie co 1 godzinę)
- **Minimalna Cena Kontraktu:** > 0.30 USD
- **Skala:** Celsius (Brak konwersji Fahrenheit, rynek Non-US)

### Wyniki Symulacji dla Najwyższej Temperatury (MAX)

**Zakłady 1-dniowe (Day 1 Ahead):**
- **ROI > 30%:** Ilość zakładów: 44 | Win Rate: 47.7% | Zysk netto: $-131.00 | ROI: -5.98%
- **ROI > 40%:** Ilość zakładów: 41 | Win Rate: 43.9% | Zysk netto: $-182.50 | ROI: -9.38%
- **ROI > 50%:** Ilość zakładów: 37 | Win Rate: 40.5% | Zysk netto: $-196.50 | ROI: -11.79%

**Zakłady 2-dniowe (Day 2 Ahead):**
- **ROI > 30%:** Ilość zakładów: 40 | Win Rate: 45.0% | Zysk netto: $-168.50 | ROI: -8.72%
- **ROI > 40%:** Ilość zakładów: 38 | Win Rate: 42.1% | Zysk netto: $-197.50 | ROI: -11.19%
- **ROI > 50%:** Ilość zakładów: 34 | Win Rate: 38.2% | Zysk netto: $-218.00 | ROI: -14.61%

**Wnioski:**
Mimo że rynek w Nowej Zelandii rozliczany jest całkowicie w systemie metrycznym (Celsjusze) i ominęliśmy w ten sposób "pułapkę" amerykańskich ułamków Fahrenheita (jak w Chicago), Wellington okazuje się być rynkiem absolutnie nieprzewidywalnym dla naszych hybryd.

W każdej testowanej konfiguracji ponosimy twarde straty (-6% do -15% ROI), a celność modelu ledwo ociera się o 47% przy najłagodniejszych kryteriach, spadając do zaledwie 38% na celach dwudniowych i wysokich wymogach ROI. Słynne zjawisko gwałtownych wiatrów w Cieśninie Cooka w Wellington (najbardziej wietrzne miasto świata) powoduje ogromne turbulencje i błędy pomiarowe ECMWF na stacjach lądowych w stosunku do tego, co zakłada tłum na giełdzie Polymarket.

**Rekomendacja:** 
Bezwzględny zakaz handlu automatycznego na parametrach MAX dla Wellington. Rynek ten dołącza do San Francisco jako strefa wysoce ryzykowna, w której przewidywania globalnych modeli pogodowych są nieustannie "rozdmuchiwane" przez mikroklimat. Model wyłączony z potoku produkcyjnego.
