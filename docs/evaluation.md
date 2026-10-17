# Evaluarea modelelor

Acest document descrie cum sunt evaluate predicțiile din PitchSense și prezintă rezultatele pentru La Liga. Rezultatele celorlalte patru ligi și comparația dintre ligi sunt în `docs/leagues.md`. Măsurile sunt implementate de noi în `app/evaluation/metrics.py`, iar evaluarea este făcută de `app/evaluation/evaluator.py`.

## 1. Condițiile evaluării

- **Meciurile:** cele 6.080 de meciuri din sezoanele de evaluare 2010/11–2025/26 (La Liga). Sezonul de încălzire 2006/07 și sezoanele de calibrare 2007/08–2009/10 nu sunt evaluate.
- **Predicțiile:** făcute cronologic (walk-forward). Fiecare model folosește doar meciurile dinaintea zilei meciului prezis (`docs/architecture.md`, secțiunile 7–8).
- **Condiții identice:** toate modelele sunt evaluate pe exact aceleași meciuri. Toate cele 6.080 de meciuri au predicții de la toate cele trei modele, deci niciun meci nu a fost exclus.
- **Modelele:** ratingul Elo, modelul Poisson, regresia logistică și două referințe: „frecvențele trecute” (frecvențele rezultatelor în ultimele 380 de meciuri ale ligii) și „mereu victoria gazdelor”. Din Faza 23, modelele sunt comparate și cu casele de pariuri (secțiunea 3.4), ca reper exterior.

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

| Acuratețea când modelul e sigur (Faza 23) | acuratețea doar pe meciurile în care cea mai mare probabilitate a modelului este cel puțin un prag (50%, 60%, 65%, 70%), cu numărul acestor meciuri | răspunde la întrebarea „cât de des nimerește modelul când e sigur?”; un model bine calibrat nimerește cel puțin cât arată pragul, dar doar pe o parte din meciuri |

Valori de referință: o predicție de 1/3 pentru fiecare rezultat are scorul Brier 2/3 = 0,667 și pierderea logaritmică $\ln 3 = 1{,}0986$, orice s-ar întâmpla.

Fiecare medie este însoțită de eroarea ei standard: abaterea standard a valorilor pe meci împărțită la $\sqrt{n}$. „Mereu victoria gazdelor” dă probabilitatea 0 egalurilor și victoriilor oaspeților, deci este evaluată doar prin acuratețe și matricea de confuzie.

## 3. Rezultate

Rulare din 2026-10-16 (`python -m app.evaluation.backtesting`, apoi `python -m app.evaluation.evaluator SP1`), cu setările din Faza 23: Elo cu ponderea diferenței de goluri ($K = 10$, $H = 80$), Poisson cu ponderi pentru meciurile recente și corecția Dixon–Coles ($N = 76$, $m = 10$, $h = 19$, $\rho = -0{,}04$), regresia logistică cu șapte caracteristici ($\lambda = 0{,}1$). Valorile sunt de forma medie ± eroare standard; la scorul Brier și la pierderea logaritmică, mai mic înseamnă mai bine.

| Model | Acuratețe | Scor Brier | Pierdere logaritmică | Eroare de calibrare | Eroarea golurilor |
|---|---|---|---|---|---|
| Elo | 53,6% ± 0,6% | 0,5783 ± 0,0049 | 0,9765 ± 0,0075 | 0,0252 | – |
| Poisson | 53,2% ± 0,6% | 0,5819 ± 0,0038 | 0,9779 ± 0,0053 | 0,0137 | 0,8886 ± 0,0064 |
| Regresie logistică | 53,8% ± 0,6% | 0,5762 ± 0,0043 | 0,9700 ± 0,0062 | 0,0124 | – |
| Frecvențele trecute | 46,6% ± 0,6% | 0,6405 ± 0,0026 | 1,0613 ± 0,0038 | 0,0103 | – |
| Mereu victoria gazdelor | 46,6% ± 0,6% | – | – | – | – |

Înainte de Faza 23 (rulare din 2026-10-05), valorile erau: Elo 53,4% / 0,5776 / 0,9735; Poisson 52,6% / 0,5827 / 0,9794; regresia logistică 53,6% / 0,5777 / 0,9721. Comparate meci cu meci, schimbările din La Liga sunt: Elo +0,0007 la scorul Brier (nicio diferență reală), Poisson −0,0008 (nicio diferență reală), regresia logistică −0,0015 (o îmbunătățire reală, intervalul [−0,0024; −0,0005]).

### 3.1. Matricele de confuzie

Rândurile sunt rezultatele reale, coloanele cele prezise. Din cele 6.080 de meciuri, 2.836 au fost victorii ale gazdelor, 1.522 egaluri (25,0%) și 1.722 victorii ale oaspeților.

| Model | Real H → prezis H / D / A | Real D → prezis H / D / A | Real A → prezis H / D / A |
|---|---|---|---|
| Elo | 2.434 / 0 / 402 | 1.073 / 0 / 449 | 899 / 0 / 823 |
| Poisson | 2.528 / 0 / 308 | 1.183 / 2 / 337 | 1.018 / 0 / 704 |
| Regresie logistică | 2.501 / 0 / 335 | 1.142 / 0 / 380 | 954 / 0 / 768 |
| Frecvențele trecute | 2.836 / 0 / 0 | 1.522 / 0 / 0 | 1.722 / 0 / 0 |
| Mereu victoria gazdelor | 2.836 / 0 / 0 | 1.522 / 0 / 0 | 1.722 / 0 / 0 |

### 3.2. Calibrarea

Pentru fiecare interval: media probabilităților prezise / frecvența reală (numărul de afirmații).

| Interval | Elo | Poisson | Regresie logistică |
|---|---|---|---|
| 0–10% | 5,7% / 9,3% (1.469) | 7,6% / 5,2% (383) | 6,8% / 5,8% (755) |
| 10–20% | 15,9% / 18,0% (3.047) | 16,1% / 13,7% (2.075) | 15,9% / 15,2% (2.623) |
| 20–30% | 25,8% / 27,6% (6.555) | 25,6% / 25,0% (7.673) | 25,3% / 26,6% (7.275) |
| 30–40% | 34,9% / 33,8% (1.797) | 34,3% / 33,7% (3.076) | 34,9% / 32,9% (2.328) |
| 40–50% | 44,8% / 41,9% (1.696) | 44,9% / 45,4% (2.308) | 44,8% / 43,9% (2.113) |
| 50–60% | 53,8% / 50,2% (1.300) | 54,5% / 57,4% (1.535) | 54,5% / 53,2% (1.420) |
| 60–70% | 64,6% / 58,6% (1.110) | 64,3% / 68,7% (731) | 64,6% / 66,0% (920) |
| 70–80% | 75,1% / 70,6% (724) | 74,5% / 83,5% (334) | 74,4% / 75,3% (457) |
| 80–90% | 85,5% / 82,8% (447) | 83,4% / 89,5% (124) | 84,9% / 87,1% (294) |
| 90–100% | 91,3% / 89,5% (95) | 90,7% / 100% (1) | 91,1% / 89,1% (55) |

### 3.3. Când modelul e sigur

Acuratețea pe meciurile în care cea mai mare probabilitate a modelului era cel puțin pragul, apoi numărul acestor meciuri și partea lor din cele 6.080:

| Model | Peste 50% | Peste 60% | Peste 65% | Peste 70% |
|---|---|---|---|---|
| Elo | 61,7% (3.676; 60%) | 68,0% (2.376; 39%) | 72,3% (1.764; 29%) | 76,3% (1.266; 21%) |
| Poisson | 65,1% (2.725; 45%) | 75,0% (1.190; 20%) | 79,6% (749; 12%) | 85,2% (459; 8%) |
| Regresie logistică | 64,0% (3.146; 52%) | 72,8% (1.726; 28%) | 77,0% (1.201; 20%) | 80,5% (806; 13%) |
| Casele de pariuri | 66,5% (2.915; 48%) | 75,5% (1.623; 27%) | 79,4% (1.163; 19%) | 81,8% (804; 13%) |

„Frecvențele trecute” trec de 50% doar în 848 de meciuri (48,7% nimerite) și niciodată de 60%. Pe toate meciurile, niciun model nu trece de 54%, dar pe meciurile în care e sigur trece de 70%: regresia logistică nimerește 77,0% din cele 1.201 meciuri la care dădea cel puțin 65%, adică un meci din cinci. Precizia mare vine deci cu o acoperire mică; ea nu se adună la acuratețea pe toate meciurile, care rămâne cea din secțiunea 3.

### 3.4. Față de casele de pariuri

Fișierele Football-Data.co.uk conțin media cotelor caselor de pariuri pentru fiecare meci, luate înainte de meci: `BbAvH`, `BbAvD`, `BbAvA` (Betbrain) până în 2018/19 și `AvgH`, `AvgD`, `AvgA` din 2019/20. Cotele sunt transformate în probabilități ($1/\text{cotă}$), iar marja caselor (suma lor trece de 1) este scoasă proporțional: $p_c = (1/o_c) / \sum_k (1/o_k)$. Rezultatul, „Casele de pariuri”, este evaluat cu aceleași măsuri, pe meciurile de evaluare care au cote (toate cele 6.080 în La Liga). Cotele sunt păstrate într-un tabel separat al bazei de date (`market_odds`) și nu intră în niciun model: ele sunt doar un reper, cea mai bună predicție publică dinaintea meciului. Pariurile rămân în afara proiectului.

| Model | Acuratețe | Scor Brier | Pierdere logaritmică | Peste 65% |
|---|---|---|---|---|
| Elo | 53,6% | 0,5783 | 0,9765 | 72,3% din 1.764 |
| Poisson | 53,2% | 0,5819 | 0,9779 | 79,6% din 749 |
| Regresie logistică | 53,8% | 0,5762 | 0,9700 | 77,0% din 1.201 |
| Casele de pariuri | 54,6% | 0,5660 | 0,9547 | 79,4% din 1.163 |

Diferența meci cu meci a scorului Brier față de casele de pariuri (interval de 95%): Elo +0,0123 [+0,0090; +0,0156], Poisson +0,0158 [+0,0128; +0,0188], regresia logistică +0,0102 [+0,0076; +0,0127], frecvențele trecute +0,0745 [+0,0677; +0,0813]. Toate sunt reale: casele de pariuri prezic mai bine decât fiecare model. Distanța de la regresia logistică la ele (0,0102) este însă de peste șase ori mai mică decât cea de la frecvențele trecute la regresia logistică (0,0643). Celelalte ligi: `docs/leagues.md`, secțiunea 6.

## 4. Observații

- **Toate cele trei modele sunt clar mai bune decât referințele.** Pe toate măsurile probabilistice, diferența față de „frecvențele trecute” (Brier 0,6405, pierdere logaritmică 1,0613) este de peste zece ori mai mare decât erorile standard. Acuratețea crește de la 46,6% la 53,2–53,8%.
- **Regresia logistică are cele mai bune valori, dar nu se deosebește real de Elo.** Diferența dintre ele este 0,0021 la scorul Brier, cu intervalul [−0,0003; +0,0045] (`docs/leagues.md`). Regresia logistică folosește diferența Elo ca intrare, deci rezultatele apropiate sunt firești.
- **Modelul Poisson este puțin în urmă** la acuratețe, scorul Brier și pierderea logaritmică. Cel mai bine calibrat dintre cele trei modele este acum regresia logistică (eroarea de calibrare 0,0124), urmată de Poisson (0,0137).
- **Egalul aproape niciodată nu este rezultatul cel mai probabil.** Doar Poisson, cu corecția Dixon–Coles, a pus egalul pe primul loc în două meciuri (amândouă au fost egaluri); restul celor 1.522 de egaluri (25,0% din meciuri) sunt ratate de acuratețe. Probabilitățile egalurilor sunt totuși realiste, iar scorul Brier și pierderea logaritmică le recompensează. Acuratețea singură ascunde acest lucru.
- **Victoriile oaspeților** sunt prezise corect în 823 (Elo), 704 (Poisson) și 768 (regresia logistică) din cele 1.722 de cazuri.
- **„Frecvențele trecute” prezic mereu victoria gazdelor**, pentru că gazdele câștigă cel mai des în orice fereastră de 380 de meciuri. De aceea au exact aceeași acuratețe ca „mereu victoria gazdelor”. Sunt însă bine calibrate (0,0103), pentru că nu încearcă să deosebească meciurile între ele.
- **Calibrarea arată tendințe diferite.** Elo este prea sigur pe favoriți: afirmațiile de 60–70% s-au produs în 58,6% din cazuri, iar cele de 70–80% în 70,6%; eroarea lui de calibrare a crescut de la 0,0168 la 0,0252 odată cu ponderea golurilor. Poisson este prea prudent cu favoriții (70–80%: prezis 74,5%, real 83,5%). Regresia logistică urmează cel mai bine diagonala.
- **Golurile așteptate** ale modelului Poisson diferă în medie cu 0,889 goluri de golurile reale ale fiecărei echipe (0,891 înainte de Faza 23).

## 5. Corecție făcută în timpul evaluării

Prima rulare a evaluării a oprit calculul pierderii logaritmice a modelului Elo. Pentru meciuri foarte dezechilibrate, conversia lui Elo (Ec. 6 din `docs/algorithms/elo.md`) dădea probabilitatea exact 0 victoriei echipei slabe. Într-unul dintre aceste meciuri, Barcelona – Hércules (0–2, 11 septembrie 2010), echipa slabă a câștigat, iar pierderea logaritmică a devenit infinită.

Echipa a ales să corecteze cauza, în model: fiecare victorie păstrează acum cel puțin 1%. Corecția a schimbat doar 15 din cele 6.080 de predicții Elo (0,25%) și nu a modificat parametrii K și H sau modelul egalurilor. Pentru meciul de mai sus, Elo a prezis atunci 83,7% / 15,3% / 1,0% (cu setările din Faza 23, 86,1% / 12,9% / 1,0%). Variantele respinse au fost limitarea probabilităților în formula pierderii logaritmice (care ar fi ascuns problema) și raportarea unei pierderi infinite.

## 6. Limitări

- Evaluarea folosește o singură ligă (La Liga), deci concluziile pot să nu se aplice altor competiții.
- Erorile standard din tabel descriu fiecare model separat; ele nu arată direct dacă diferența dintre două modele este semnificativă. Pentru aceasta, Faza 10 compară modelele meci cu meci.
- Calibrarea amestecă cele trei rezultate în aceleași intervale; intervalele extreme au puține afirmații (de exemplu, 19 pentru Elo la 90–100%).
- Acuratețea depinde de regula de departajare la egalitatea probabilităților (gazde, apoi egal).
- Opțiunile din Faza 23 au fost alese doar pe cele trei sezoane de calibrare (1.140 de meciuri pe ligă), iar unele nu au ajutat pe sezoanele de evaluare (ponderea golurilor la Elo; `docs/algorithms/elo.md`, secțiunea 7.6). Ele nu au fost schimbate după ce s-au văzut rezultatele evaluării, pentru că atunci evaluarea n-ar mai fi fost cronologică.
- Comparația cu casele de pariuri folosește media cotelor luate înainte de meci, dar fișierele nu păstrează momentul exact; cotele de la începerea meciului (pe care fișierele le au doar din 2019/20) nu au fost folosite.

## 7. Reproducere

```bash
python -m app.data.build_database
python -m app.evaluation.backtesting
python -m app.evaluation.evaluator SP1
python -m app.evaluation.bookmakers SP1
```
