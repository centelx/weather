# Dziennik Wyników Symulacji - Denver

Ten plik służy do rejestrowania i śledzenia parametrów naszej strategii dla rynków pogodowych na Polymarket.

## Weryfikacja Złotej Formuły - 2026-07-09

**Parametry Wejściowe:**
- **Miasto:** Denver (USA)
- **Zakres Danych:** 2026-06-01 do 2026-07-08
- **Model:** Hybryda XGBoost + BayesianRidge (Time Isolated)
- **Run Modelu Pogodowego:** 1200 UTC / 0000 UTC
- **Minimalne Oczekiwane ROI (Edge):** > 10%
- **Minimalna Cena Kontraktu:** > 0.30 USD
- **Kara Spreadu:** +0.01 USD doliczana do wyceny rynkowej
- **Skala:** Fahrenheit

### Wyniki Symulacji dla Najwyższej Temperatury (MAX)
```text
--- RAPORT Z BACKTESTU ---
Ilość zakładów: 28
Win Rate:       89.3%
Suma stawek:    $1749.15
Zysk netto:     $700.85
Końcowy portfel:$1700.85
ROI:            40.07%
```

### Wyniki Symulacji dla Najniższej Temperatury (MIN)
```text
--- RAPORT Z BACKTESTU ---
Brak otwartych pozycji - przewaga nie przekroczyła progu.
```

**Wnioski:**
Potężny sukces koncepcji "Rynkowego Chaosu". Denver, miasto znane z drastycznych anomalii i kapryśnej pogody powodowanej bliskością Gór Skalistych, okazuje się prawdziwą żyłą złota w lecie na Polymarkecie.
- Rynek dzienny (MAX) generuje mniejszą ilość zakładów w miesiącu (28 wejść), ale ich jakość jest bezbłędna. Win Rate dobił do **niebotycznego poziomu blisko 90%**, generując czysty zysk +40.07%. Nasz algorytm wyciąga tu ogromne "Value", deklasując ludzkich traderów mylących się co do maksymalnych skoków i spadków temperatur za dnia.
- Rynek nocny (MIN) w lecie w Denver zachowuje się tak jak w innych analizowanych miastach – jest prawdopodobnie bardzo przewidywalny dla ludzi, przez co model nie uważa go za warty ataku (0 wejść przy Edge > 10%). Noc w górach widocznie rządzi się bardzo żelaznymi, łatwymi do wycenienia prawami termodynamiki.
Rekomendacja: Denver zostaje wpisane do Złotej Ligi rynków opłacalnych. Uruchamiamy na nim agresywny handel (tylko rynek MAX).
