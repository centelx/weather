# Strategia HFT Intraday: Miami

**Parametry Wejściowe:**
- **Miasto:** Miami (USA)
- **Zakres Danych:** 2024-01-01 do 2026-07-08
- **Model:** Hybryda XGBoost + BayesianRidge (Time Isolated)
- **Architektura:** HFT Intraday (Skanowanie co 1 godzinę, 10:00 - 24:00 EDT)
- **Minimalna Cena Kontraktu:** > 0.30 USD
- **Skala:** Fahrenheit

### Wyniki Symulacji dla Najwyższej Temperatury (MAX)

**Zakłady 1-dniowe (Day 1 Ahead):**
- **ROI > 30%:** Ilość zakładów: 34 | Win Rate: 50.0% | Zysk netto: $-129.55 | ROI: -7.22%
- **ROI > 40%:** Ilość zakładów: 27 | Win Rate: 51.9% | Zysk netto: $53.50   | ROI: 4.06%
- **ROI > 50%:** Ilość zakładów: 22 | Win Rate: 50.0% | Zysk netto: $35.00   | ROI: 3.36%

**Zakłady 2-dniowe (Day 2 Ahead):**
- **ROI > 30%:** Ilość zakładów: 36 | Win Rate: 50.0% | Zysk netto: $-160.55 | ROI: -8.34%
- **ROI > 40%:** Ilość zakładów: 30 | Win Rate: 50.0% | Zysk netto: $-47.50  | ROI: -3.13%
- **ROI > 50%:** Ilość zakładów: 25 | Win Rate: 52.0% | Zysk netto: $38.00   | ROI: 3.07%

**Wnioski:**
Weryfikacja na pełnym datasecie (921 dni), po skorygowaniu metodologii całkowania temperatur (prawo zaokrąglania +0.5 / +1.5 Fahrenheita w Wunderground), ostatecznie obala mit o potężnych zyskach w Miami. 
Zamiast 80% Win Rate, brutalna rzeczywistość obnaża rynek, który zachowuje się jak rzut monetą (płaskie 50-52% skuteczności we wszystkich konfiguracjach).

Z powodu ogromnej wilgotności powietrza i morskiej bryzy na Florydzie modele ECMWF regularnie pudłują. Jedyne opłacalne, dodatnie progi pojawiają się wyłącznie, gdy zmusimy bota do szukania ekstremalnie lukratywnych okazji (ROI > 40% lub ROI > 50%). Wtedy 50% Win Rate wystarcza na wygenerowanie ledwie 3-4% ROI (zabezpieczonego tylko dlatego, że wchodzimy tylko w kursy, przy których "rzut monetą" wciąż nam płaci).

**Rekomendacja:** 
Miami przypomina nieco profil z Denver - skuteczność wynosi 50%. Jeśli chcemy mieć Florydę w portfolio, możemy uruchomić bota WYŁĄCZNIE dla ustawień **Day 1 i Day 2 z żelaznym wymogiem ROI > 50%**, by ledwo utrzymać głowę nad wodą i generować minimalne, zachowawcze stopnie zwrotu.
