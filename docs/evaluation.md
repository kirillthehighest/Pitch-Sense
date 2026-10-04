# Evaluarea modelelor

Acest document descrie cum sunt evaluate predicțiile din PitchSense și prezintă rezultatele. Măsurile sunt implementate de noi în `app/evaluation/metrics.py`, iar evaluarea este făcută de `app/evaluation/evaluator.py`.

## 1. Condițiile evaluării

- **Meciurile:** cele 6.080 de meciuri din sezoanele de evaluare 2010/11–2025/26 (La Liga). Sezonul de încălzire 2006/07 și sezoanele de calibrare 2007/08–2009/10 nu sunt evaluate.
- **Predicțiile:** făcute cronologic (walk-forward). Fiecare model folosește doar meciurile dinaintea zilei meciului prezis (`docs/architecture.md`, secțiunile 7–8).
- **Condiții identice:** toate modelele sunt evaluate pe exact aceleași meciuri. Toate cele 6.080 de meciuri au predicții de la toate cele trei modele, deci niciun meci nu a fost exclus.
- **Modelele:** ratingul Elo, modelul Poisson, regresia logistică și două referințe: „frecvențele trecute” (frecvențele rezultatelor în ultimele 380 de meciuri ale ligii) și „mereu victoria gazdelor”.

## 2. Măsurile folosite

Notații: $n$ — numărul de meciuri; pentru meciul $i$, $p_i = (p_{iH}, p_{iD}, p_{iA})$ sunt probabilitățile prezise, iar $e_i$ este rezultatul real scris ca vector (de exemplu $(1, 0, 0)$ pentru victoria gazdelor).

| Măsură | Definiție | De ce o folosim |
|---|---|---|
| Acuratețea | fracțiunea meciurilor în care rezultatul cel mai probabil s-a produs (la egalitate: gazde, apoi egal) | intuitivă; arată cât de des „ghicește” modelul, dar ignoră încrederea predicției |
| Scorul Brier | $\frac{1}{n} \sum_i \sum_{c} (p_{ic} - e_{ic})^2$, între 0 (perfect) și 2 | evaluează întregul vector de probabilități, nu doar rezultatul ales |
| Pierderea logaritmică | $\frac{1}{n} \sum_i -\ln p_{i, y_i}$ | penalizează puternic predicțiile sigure pe sine și greșite; este infinită dacă un rezultat produs avea probabilitatea 0 |
| Matricea de confuzie | numărul de meciuri pentru fiecare pereche (rezultat real, rezultat prezis) | arată ce rezultate rată fiecare model |
| Calibrarea | fiecare pereche (meci, rezultat) este o afirmație probabilistică; în fiecare interval de probabilitate (0–10%, 10–20%, …) se compară media probabilităților cu frecvența reală | verifică dacă „60%” se întâmplă cu adevărat în aproximativ 60% din cazuri |
| Eroarea de calibrare (ECE) | $\sum_b \frac{N_b}{N} \lvert \bar{p}_b - \bar{o}_b \rvert$ | rezumă calibrarea într-un singur număr |
| Eroarea golurilor așteptate | media lui $\lvert \lambda - \text{goluri reale} \rvert$, pentru gazde și oaspeți | doar pentru modelul Poisson, care prezice numărul de goluri |

Valori de referință: o predicție de 1/3 pentru fiecare rezultat are scorul Brier 2/3 = 0,667 și pierderea logaritmică $\ln 3 = 1{,}0986$, orice s-ar întâmpla.

Fiecare medie este însoțită de eroarea ei standard: abaterea standard a valorilor pe meci împărțită la $\sqrt{n}$. „Mereu victoria gazdelor” dă probabilitatea 0 egalurilor și victoriilor oaspeților, deci este evaluată doar prin acuratețe și matricea de confuzie.

## 3. Rezultate

Rulare din 2026-10-04 (`python -m app.evaluation.backtesting`, apoi `python -m app.evaluation.evaluator`). Valorile sunt de forma medie ± eroare standard; la scorul Brier și la pierderea logaritmică, mai mic înseamnă mai bine.

| Model | Acuratețe | Scor Brier | Pierdere logaritmică | Eroare de calibrare | Eroarea golurilor |
|---|---|---|---|---|---|
| Elo | 53,4% ± 0,6% | 0,5776 ± 0,0047 | 0,9735 ± 0,0069 | 0,0168 | – |
| Poisson | 52,8% ± 0,6% | 0,5849 ± 0,0037 | 0,9826 ± 0,0052 | 0,0132 | 0,8920 ± 0,0065 |
| Regresie logistică | 53,6% ± 0,6% | 0,5777 ± 0,0042 | 0,9721 ± 0,0059 | 0,0158 | – |
| Frecvențele trecute | 46,6% ± 0,6% | 0,6405 ± 0,0026 | 1,0613 ± 0,0038 | 0,0103 | – |
| Mereu victoria gazdelor | 46,6% ± 0,6% | – | – | – | – |

### 3.1. Matricele de confuzie

Rândurile sunt rezultatele reale, coloanele cele prezise. Din cele 6.080 de meciuri, 2.836 au fost victorii ale gazdelor, 1.522 egaluri (25,0%) și 1.722 victorii ale oaspeților.

| Model | Real H → prezis H / D / A | Real D → prezis H / D / A | Real A → prezis H / D / A |
|---|---|---|---|
| Elo | 2.455 / 0 / 381 | 1.100 / 0 / 422 | 931 / 0 / 791 |
| Poisson | 2.542 / 0 / 294 | 1.196 / 0 / 326 | 1.052 / 0 / 670 |
| Regresie logistică | 2.486 / 0 / 350 | 1.138 / 0 / 384 | 950 / 0 / 772 |
| Frecvențele trecute | 2.836 / 0 / 0 | 1.522 / 0 / 0 | 1.722 / 0 / 0 |
| Mereu victoria gazdelor | 2.836 / 0 / 0 | 1.522 / 0 / 0 | 1.722 / 0 / 0 |

### 3.2. Calibrarea

Pentru fiecare interval: media probabilităților prezise / frecvența reală (numărul de afirmații).

| Interval | Elo | Poisson | Regresie logistică |
|---|---|---|---|
| 0–10% | 6,2% / 8,0% (1.136) | 7,9% / 4,9% (266) | 7,1% / 5,5% (582) |
| 10–20% | 16,1% / 17,1% (2.979) | 16,2% / 13,1% (1.972) | 15,8% / 13,7% (2.409) |
| 20–30% | 25,5% / 27,0% (6.912) | 25,3% / 25,0% (8.020) | 25,1% / 26,3% (7.589) |
| 30–40% | 35,0% / 34,1% (1.851) | 34,7% / 33,7% (2.820) | 34,9% / 32,2% (2.381) |
| 40–50% | 44,7% / 42,0% (1.714) | 44,9% / 44,9% (2.427) | 44,9% / 44,2% (2.076) |
| 50–60% | 53,8% / 51,6% (1.409) | 54,5% / 57,8% (1.619) | 54,6% / 54,1% (1.618) |
| 60–70% | 64,5% / 60,4% (1.252) | 64,1% / 67,9% (729) | 64,3% / 66,2% (944) |
| 70–80% | 75,4% / 74,4% (566) | 74,6% / 85,6% (299) | 74,4% / 78,6% (402) |
| 80–90% | 84,9% / 85,3% (402) | 82,9% / 89,8% (88) | 83,6% / 90,8% (238) |
| 90–100% | 90,5% / 84,2% (19) | – | 90,2% / 100% (1) |

## 4. Observații

- **Toate cele trei modele sunt clar mai bune decât referințele.** Pe toate măsurile probabilistice, diferența față de „frecvențele trecute” (Brier 0,6405, pierdere logaritmică 1,0613) este de peste zece ori mai mare decât erorile standard. Acuratețea crește de la 46,6% la 52,8–53,6%.
- **Elo și regresia logistică sunt practic la egalitate.** Diferența dintre ele este 0,0001 la scorul Brier și 0,0014 la pierderea logaritmică, mult sub erorile standard (aproximativ 0,005). Regresia logistică folosește diferența Elo ca intrare, deci rezultatele apropiate sunt firești.
- **Modelul Poisson este puțin în urmă** la acuratețe, scorul Brier și pierderea logaritmică, dar este cel mai bine calibrat dintre cele trei modele (eroarea de calibrare 0,0132). Dacă diferențele dintre modele sunt reale sau doar zgomot se verifică în Faza 10, prin compararea modelelor pe aceleași meciuri.
- **Niciun model nu prezice vreodată egalul ca rezultat cel mai probabil.** Coloana „prezis D” este 0 pentru toate modelele, deci cele 1.522 de egaluri (25,0% din meciuri) sunt ratate toate de acuratețe. Probabilitățile egalurilor sunt totuși realiste, iar scorul Brier și pierderea logaritmică le recompensează. Acuratețea singură ascunde acest lucru.
- **Victoriile oaspeților** sunt prezise corect în 791 (Elo), 670 (Poisson) și 772 (regresia logistică) din cele 1.722 de cazuri.
- **„Frecvențele trecute” prezic mereu victoria gazdelor**, pentru că gazdele câștigă cel mai des în orice fereastră de 380 de meciuri. De aceea au exact aceeași acuratețe ca „mereu victoria gazdelor”. Sunt însă bine calibrate (0,0103), pentru că nu încearcă să deosebească meciurile între ele.
- **Calibrarea arată tendințe diferite.** Elo este ușor prea sigur pe favoriți: afirmațiile de 60–70% s-au produs în 60,4% din cazuri. Poisson este prea prudent cu favoriții clari (70–80%: prezis 74,6%, real 85,6%) și prea generos cu rezultatele puțin probabile (0–10%: prezis 7,9%, real 4,9%). Regresia logistică este între ele.
- **Golurile așteptate** ale modelului Poisson diferă în medie cu 0,892 goluri de golurile reale ale fiecărei echipe.

## 5. Corecție făcută în timpul evaluării

Prima rulare a evaluării a oprit calculul pierderii logaritmice a modelului Elo. Pentru meciuri foarte dezechilibrate, conversia lui Elo (Ec. 6 din `docs/algorithms/elo.md`) dădea probabilitatea exact 0 victoriei echipei slabe. Într-unul dintre aceste meciuri, Barcelona – Hércules (0–2, 11 septembrie 2010), echipa slabă a câștigat, iar pierderea logaritmică a devenit infinită.

Echipa a ales să corecteze cauza, în model: fiecare victorie păstrează acum cel puțin 1%. Corecția a schimbat doar 15 din cele 6.080 de predicții Elo (0,25%) și nu a modificat parametrii K și H sau modelul egalurilor. Pentru meciul de mai sus, Elo prezice acum 83,7% / 15,3% / 1,0%. Variantele respinse au fost limitarea probabilităților în formula pierderii logaritmice (care ar fi ascuns problema) și raportarea unei pierderi infinite.

## 6. Limitări

- Evaluarea folosește o singură ligă (La Liga), deci concluziile pot să nu se aplice altor competiții.
- Erorile standard din tabel descriu fiecare model separat; ele nu arată direct dacă diferența dintre două modele este semnificativă. Pentru aceasta, Faza 10 compară modelele meci cu meci.
- Calibrarea amestecă cele trei rezultate în aceleași intervale; intervalele extreme au puține afirmații (de exemplu, 19 pentru Elo la 90–100%).
- Acuratețea depinde de regula de departajare la egalitatea probabilităților (gazde, apoi egal).

## 7. Reproducere

```bash
python -m app.data.build_database
python -m app.evaluation.backtesting
python -m app.evaluation.evaluator
```
