# Dziennik Wyników Symulacji - Wellington

Ten plik służy do rejestrowania i śledzenia parametrów naszej strategii dla rynków pogodowych na Polymarket.

## Weryfikacja Złotej Formuły - 2026-07-09

**Parametry Wejściowe:**
- **Miasto:** Wellington (Nowa Zelandia)
- **Zakres Danych:** 2026-06-01 do 2026-07-08
- **Model:** Hybryda XGBoost + BayesianRidge (Time Isolated)
- **Run Modelu Pogodowego:** 1200 UTC / 0000 UTC
- **Minimalne Oczekiwane ROI (Edge):** > 10%
- **Minimalna Cena Kontraktu:** > 0.30 USD
- **Kara Spreadu:** +0.01 USD doliczana do wyceny rynkowej
- **Skala:** Celsjusz

### Wyniki Symulacji dla Najwyższej Temperatury (MAX)
```text
--- RAPORT Z BACKTESTU ---
Ilość zakładów: 53
Win Rate:       39.6%
Suma stawek:    $2666.05
Zysk netto:     $-608.05
Końcowy portfel:$391.95
ROI:            -22.81%
```

### Wyniki Symulacji dla Najniższej Temperatury (MIN)
```text
--- RAPORT Z BACKTESTU ---
Brak otwartych pozycji - przewaga nie przekroczyła progu.
```

**Wnioski:**
Wellington zachowuje się analogicznie do rynku singapurskiego, stanowiąc skrajny przykład rynku "trudnego" (bardzo efektywnego).
- Rynek dzienny (MAX) cechuje się dramatycznie niskim Win Rate (niecałe 40%), co przy próbie gry na krawędzi opłacalności generuje potężne straty (-23%). To najgorszy wynik MAX ze wszystkich badanych miast.
- Rynek nocny (MIN) w ogóle nie generuje zagrań. Wycena nocnych spadków temperatury w Nowej Zelandii przez rynek jest tak trafna (lub kursy tak zaniżone), że model nie jest w stanie znaleźć ani jednego opłacalnego zakładu z matematycznym "Edge" > 10%.
Rekomendacja: Kolejne miasto ląduje na ostatecznej Czarnej Liście.
