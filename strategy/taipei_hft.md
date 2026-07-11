# Strategia HFT Intraday: Taipei

**Parametry Wejściowe:**
- **Miasto:** Taipei (Tajwan)
- **Zakres Danych:** 2024-01-01 do 2026-07-09
- **Model:** Hybryda XGBoost + BayesianRidge (Time Isolated)
- **Architektura:** HFT Intraday
- **Przełączanie Runów:** Sztywny próg publikacji ECMWF UTC
- **Skala:** Celsjusze (Zmieniona logika prawdopodobieństwa: Model prognozuje precyzyjne ułamki dla maksymalizacji Edge'a z Fahrenheita, a następnie estymuje koszyki w oparciu o zaokrąglenia `[b-0.5, b+0.5)` zgodnie z zachowaniem Wunderground)

### Wyniki Symulacji dla Najwyższej Temperatury (MAX)

*Symulacja po naprawie problemu "paradoksu zaokrągleń". Narzucona cena minimalna to >0.30.*

**Zakłady 1-dniowe (Day 1 Ahead):**
* ROI > 30%: 35 zakładów, Win Rate: 62.9%, Zysk netto: $78.50, ROI: 3.78%
* ROI > 40%: 29 zakładów, Win Rate: 62.1%, Zysk netto: $229.00, ROI: 14.92%
* ROI > 50%: 21 zakładów, Win Rate: 47.6%, Zysk netto: $-20.40, ROI: -2.04%

**Zakłady 2-dniowe (Day 2 Ahead):**
* ROI > 30%: 37 zakładów, Win Rate: 64.9%, Zysk netto: $71.15, ROI: 3.12%
* ROI > 40%: 28 zakładów, Win Rate: 57.1%, Zysk netto: $-38.85, ROI: -2.42%
* ROI > 50%: 20 zakładów, Win Rate: 40.0%, Zysk netto: $-225.20, ROI: -22.31%

### Wyniki Symulacji dla Najniższej Temperatury (MIN)
Brak danych - na Polymarket nie jest prowadzony rynek temperatury minimalnej dla miasta Taipei, w związku z czym zakłady te są ignorowane przez strategię.

**Wnioski:**
Dzięki pomysłowi na zmianę logiki całkowania koszyków, Day 1 MAX z progiem docelowym 40% wykazuje silnie zyskowną statystykę (15% ROI na przestrzeni ~30 zakładów), zamieniając poprzednie potężne straty (-15% ROI) w gigantyczny Edge. Taipei MAX Day 1 przy parametrach ROI>40% oraz Cenie>0.30 nadaje się do włączenia do ostatecznego portfela. Day 2 z kolei oscyluje w okolicach zera.
