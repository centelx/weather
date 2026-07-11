# Strategia HFT Intraday: Singapore

**Parametry Wejściowe:**
- **Miasto:** Singapur
- **Zakres Danych:** 2024-01-01 do 2026-07-08
- **Model:** Hybryda XGBoost + BayesianRidge (Time Isolated)
- **Run Modelu Pogodowego:** 1200 UTC / 0000 UTC
- **Skala:** Celsjusz (Zastosowano matematyczne przesunięcie okna prawdopodobieństwa `[b-0.5, b+0.5]` oraz wysoką precyzję ułamków do treningu z danych Fahrenheita).

### Wyniki Symulacji dla Najwyższej Temperatury (MAX)

*Twardy warunek: Minimalna cena kontraktu na Polymarket > 0.30 USD.*

**Zakłady 1-dniowe (Day 1 Ahead):**
* ROI > 30%: 32 zakłady, Win Rate: 53.1%, Zysk netto: $-4.00, ROI: -0.24%
* ROI > 40%: 21 zakładów, Win Rate: 57.1%, Zysk netto: $175.00, ROI: 17.48%
* ROI > 50%: 17 zakładów, Win Rate: 64.7%, Zysk netto: $291.50, ROI: 37.06%

**Zakłady 2-dniowe (Day 2 Ahead):**
* ROI > 30%: 40 zakładów, Win Rate: 47.5%, Zysk netto: $-310.50, ROI: -14.29%
* ROI > 40%: 30 zakładów, Win Rate: 46.7%, Zysk netto: $-104.50, ROI: -7.08%
* ROI > 50%: 19 zakładów, Win Rate: 57.9%, Zysk netto: $195.50, ROI: 22.15%

### Wyniki Symulacji dla Najniższej Temperatury (MIN)
Brak rozliczeń na Polymarket dla temperatury minimalnej w Singapurze, więc w backteście ten wariant został pominięty.

**Wnioski:**
Singapur to kolejny rynek Celsjusza, który "eksplodował" zyskownością zaraz po zastosowaniu ułamków przy nauce i uwzględnieniu zaokrąglania. Przy agresywnym szukaniu ROI pow. 50%, wyciągamy wprost gigantycznego Edge'a (+37% zysku kapitału na zaledwie 17 strzałach dla Day 1, i +22% dla Day 2). Zalecam dołączenie obu wariantów (Day 1 i Day 2) ze sztywnym progiem wejścia ustawionym na 50% ROI.
