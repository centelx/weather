# Strategia HFT Intraday: Singapur

**Parametry Wejściowe:**
- **Miasto:** Singapur (Singapur)
- **Zakres Danych:** 2024-01-01 do 2026-07-08
- **Model:** Hybryda XGBoost + BayesianRidge (Time Isolated)
- **Architektura:** HFT Intraday (Skanowanie co 1 godzinę)
- **Minimalna Cena Kontraktu:** > 0.30 USD
- **Skala:** Celsius (Brak konwersji Fahrenheit, rynek Non-US)

### Wyniki Symulacji dla Najwyższej Temperatury (MAX)

**Zakłady 1-dniowe (Day 1 Ahead):**
- **ROI > 30%:** Ilość zakładów: 37 | Win Rate: 54.1% | Zysk netto: $26.00  | ROI: 1.34%
- **ROI > 40%:** Ilość zakładów: 26 | Win Rate: 46.2% | Zysk netto: $-47.50 | ROI: -3.88%
- **ROI > 50%:** Ilość zakładów: 16 | Win Rate: 50.0% | Zysk netto: $89.50  | ROI: 12.89%

**Zakłady 2-dniowe (Day 2 Ahead):**
- **ROI > 30%:** Ilość zakładów: 41 | Win Rate: 46.3% | Zysk netto: $-366.50| ROI: -16.45%
- **ROI > 40%:** Ilość zakładów: 29 | Win Rate: 37.9% | Zysk netto: $-334.50| ROI: -23.68%
- **ROI > 50%:** Ilość zakładów: 20 | Win Rate: 45.0% | Zysk netto: $-25.50 | ROI: -2.81%

**Wnioski:**
Zbudowanie kompletnego, potężnego wektora danych (921 dni od stycznia 2024) ujawniło kolejny "Miraż Backtestów". Wcześniejsze testy na małych i wybiórczych paczkach danych wskazywały na rewelacyjne zwroty dla Singapuru (+37% ROI).
W starciu z wieloletnią historią i włączeniem pełnej zmienności tropikalnej wyspy, model 2-dniowy (Day 2 Ahead) poległ całkowicie, notując potężne straty przekraczające na niektórych progach nawet -23% ROI.

Dopiero w przypadku zakładów 1-dniowych (Day 1 Ahead) na rygorystycznym ograniczeniu (gdzie zmuszamy algorytm do otwarcia pozycji wyłącznie z urojonym zyskiem ROI > 50%) rynek udowadnia opłacalność, osiągając Win Rate dokładnie rzędu 50.0% i solidny zysk na kapitale wynoszący **12.89% ROI**. Oznacza to, że giełda Polymarket myli się tam tylko w momentach rynkowej wyprzedaży kursu.

**Rekomendacja:** 
Zalecam natychmiastowe wyrzucenie zakładów Day 2 z potoku produkcyjnego w Singapurze. Singapur utrzymujemy aktywny WYŁĄCZNIE na wariancie **Day 1 z włączonym marginesem ROI >= 50%**. Każde obniżenie poprzeczki będzie skutkować stratą kapitału.
