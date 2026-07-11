# Dziennik Wyników Symulacji - Paryż

Ten plik służy do rejestrowania i śledzenia parametrów naszej strategii dla rynków pogodowych na Polymarket.

## Weryfikacja Złotej Formuły - 2026-07-09

**Parametry Wejściowe:**
- **Miasto:** Paryż (Francja)
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
Ilość zakładów: 40
Win Rate:       52.5%
Suma stawek:    $2424.00
Zysk netto:     $-366.00
Końcowy portfel:$634.00
ROI:            -15.10%
```

### Wyniki Symulacji dla Najniższej Temperatury (MIN)
```text
--- RAPORT Z BACKTESTU ---
Ilość zakładów: 51
Win Rate:       66.7%
Suma stawek:    $3092.70
Zysk netto:     $239.30
Końcowy portfel:$1239.30
ROI:            7.74%
```

**Wnioski:**
Zestawienie dla Paryża perfekcyjnie wpasowuje się w tezę wysuniętą przy analizie rynku londyńskiego: rynki europejskie są niesamowicie trudne do pobicia i ekstremalnie efektywne pod względem poprawnej wyceny kontraktów pogodowych na Polymarket.
- Rynek dzienny (MAX) z wynikiem -15.10% udowadnia, że za dnia giełda doskonale wie co robi i bezwzględnie egzekwuje wysoką marżę dla zakładów z błędnie zawyżonym modelem prawdopodobieństwa.
- Rynek nocny (MIN) w Paryżu to w zasadzie kopia rynku z Londynu: gigantyczna ilość rzutów (51 zakładów) przy dość dobrej skuteczności 67% owocuje ROI na poziomie 7.74%. Margines zarobku nie jest rekompensatą dla tak ogromnego wolumenu zamrożonego kapitału.
Rekomendacja: Dopisać Paryż do "czarnej listy" rynków na starym kontynencie. Wyceny są zbyt bliskie ideałowi, by wyciągnąć tutaj silną, asymetryczną przewagę statystyczną.
