# Strategia HFT Intraday: Paryż

**Parametry Wejściowe:**
- **Miasto:** Paryż (Francja)
- **Zakres Danych:** 2024-01-01 do 2026-07-08
- **Model:** Hybryda XGBoost + BayesianRidge (Time Isolated)
- **Architektura:** HFT Intraday (Skanowanie co 1 godzinę)
- **Minimalna Cena Kontraktu:** > 0.30 USD
- **Skala:** Celsjusz (Brak konwersji Fahrenheit, rynek Non-US)

### Wyniki Symulacji dla Najwyższej Temperatury (MAX)

**Zakłady 1-dniowe (Day 1 Ahead):**
- **ROI > 30%:** Ilość zakładów: 36 | Win Rate: 63.9% | Zysk netto: $-34.00 | ROI: -1.49%
- **ROI > 40%:** Ilość zakładów: 29 | Win Rate: 58.6% | Zysk netto: $-71.55 | ROI: -4.12%
- **ROI > 50%:** Ilość zakładów: 18 | Win Rate: 61.1% | Zysk netto: $71.50  | ROI: 7.10%

**Zakłady 2-dniowe (Day 2 Ahead):**
- **ROI > 30%:** Ilość zakładów: 33 | Win Rate: 63.6% | Zysk netto: $-24.00 | ROI: -1.15%
- **ROI > 40%:** Ilość zakładów: 26 | Win Rate: 53.8% | Zysk netto: $-167.55| ROI: -10.88%
- **ROI > 50%:** Ilość zakładów: 17 | Win Rate: 52.9% | Zysk netto: $-87.50 | ROI: -9.03%

**Wnioski:**
Rozszerzony i prawidłowy backtest na złączonym potoku połatanych wektorów po raz kolejny utarł nosa pierwotnym szacunkom. Europa (Paryż) okazała się dużo mniej przewidywalna, niż można by sądzić. Wyniki dla wariantu Day 2 (przewidywania 48 godzin do przodu) bezustannie generują twarde straty ucinające portfel o nawet -10% netto.

Sytuację można uratować wyłącznie na predykcjach Day 1 i tylko przy ustawieniu maksymalnego marginesu błędu. Ekstremalny pułap wejścia (kiedy oczekujemy od kursu na Polymarkecie ponad 50% czystego zarobku) pozwolił oddzielić ziarno od plew i zawrzeć zyskowną próbkę 18 wyselekcjonowanych trade'ów. Wygenerowały one 7.10% czystego zysku przy Win Rate rzędu 61.1%.

**Rekomendacja:** 
Odłączamy moduł Day 2 od Paryża - ten rynek dla podwójnego horyzontu czasowego uznajemy za ryzykowny.
Zezwalamy modelowi na pracę **wyłącznie w wariancie Day 1** z absolutnym wymogiem wejścia ustawionym na poprzeczkę **ROI >= 50%**. Paryż dołącza do puli miast "wysoce nadzorowanych", gdzie handlujemy tylko najpewniejszymi, skrajnymi anomaliami rynku.
