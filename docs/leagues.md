# Comparația ligilor

Acest document compară cele cinci ligi din PitchSense: cum arată fotbalul în fiecare dintre ele și cât de bine funcționează aceiași algoritmi în fiecare. Toate ligile folosesc aceleași perioade (încălzire 2006/07, calibrare 2007/08–2009/10, evaluare 2010/11–2025/26), aceeași procedură de calibrare și aceleași măsuri (`docs/evaluation.md`). Analiza este făcută de `app/evaluation/leagues.py`, iar comparația cu casele de pariuri de `app/evaluation/bookmakers.py`. Toate valorile provin din rularea din 2026-10-16, cu setările din Faza 23; secțiunea 5.1 arată ce s-a schimbat față de rularea din 2026-10-05.

## 1. Ligile și datele

| Ligă | Cod | Echipe | Meciuri (2006/07–2025/26) | Meciuri de evaluare | Observații |
|---|---|---|---|---|---|
| Premier League (Anglia) | `E0` | 20 | 7.600 | 6.080 | – |
| La Liga (Spania) | `SP1` | 20 | 7.600 | 6.080 | – |
| Serie A (Italia) | `I1` | 20 | 7.600 | 6.080 | sezonul 2019/20 s-a încheiat pe 2 august 2020 |
| Bundesliga (Germania) | `D1` | 18 | 6.120 | 4.896 | – |
| Ligue 1 (Franța) | `F1` | 20, apoi 18 din 2023/24 | 7.277 | 5.757 | sezonul 2019/20 oprit după 279 de meciuri; 2006/07 fără statistici de șuturi |
| **Total** | | | **36.197** | **28.893** | |

Detaliile despre fișiere sunt în `data/raw/README.md`, iar regulile de verificare în `docs/architecture.md`, secțiunea 13.

## 2. Calibrarea pe fiecare ligă

Fiecare ligă își alege hiperparametrii pe propriile sezoane de încălzire și calibrare (`python -m app.evaluation.league_calibration`), cu aceleași grile și aceleași măsuri ca La Liga (`docs/algorithms/`). Ferestrele de „un sezon” urmează mărimea ligii: 380 de meciuri și 19 meciuri acasă pe echipă la 20 de echipe, 306 și 17 la 18 echipe. Din Faza 23, grilele conțin și opțiunile cerute de echipă: ponderea diferenței de goluri la Elo ($G$), ponderile meciurilor recente ($h$) și corecția Dixon–Coles ($\rho$) la Poisson și cele două caracteristici în plus ale regresiei logistice. Rulare din 2026-10-16:

| Ligă | Elo: K, H, G | Poisson: N, m, h, ρ | Regresie logistică: L2, caracteristici în plus |
|---|---|---|---|
| Premier League | 15, 80, da | 76, 5, 19, −0,08 | 0,1; golurile așteptate |
| La Liga | 10, 80, da | 76, 10, 19, −0,04 | 0,1; distanța Elo și golurile așteptate |
| Serie A | 20, 100, nu | 38, 20, –, −0,06 | 0,1; golurile așteptate |
| Bundesliga | 10, 60, da | 68, 10, 34, −0,06 | 0,1; niciuna |
| Ligue 1 | 15, 60, nu | 57, 20, 19, −0,10 | 0,1; niciuna |

Măsurile pe sezoanele de calibrare; în paranteză este referința fiecărui model: predicția constantă pentru Elo, mediile ligii pentru Poisson și frecvențele din sezonul de încălzire pentru regresia logistică.

| Ligă | Elo: eroarea pătratică medie | Poisson: media lui $-\ln P(\text{scorul real})$ | Regresie logistică: pierderea logaritmică |
|---|---|---|---|
| Premier League | 0,13870 (0,17496) | 2,87301 (3,00502) | 0,94132 (1,05548) |
| La Liga | 0,15946 (0,18101) | 2,94878 (3,02654) | 0,98299 (1,04696) |
| Serie A | 0,14982 (0,16792) | 2,80915 (2,86037) | 0,99389 (1,05130) |
| Bundesliga | 0,16269 (0,17873) | 2,99067 (3,06146) | 1,02265 (1,06817) |
| Ligue 1 | 0,15589 (0,17204) | 2,74267 (2,78241) | 1,03442 (1,07721) |

- **Avantajul terenului propriu** ales pentru Elo este cel mai mare în Serie A ($H = 100$) și cel mai mic în Bundesliga și Ligue 1 ($H = 60$).
- **Ponderea diferenței de goluri** a fost aleasă în trei ligi; acolo $K$ a scăzut (Premier League 25 → 15, La Liga și Bundesliga 15 → 10), pentru că $G \ge 1$ înmulțește $K$. Serie A și Ligue 1 și-au păstrat Elo-ul de dinainte.
- **Corecția Dixon–Coles** a fost aleasă în toate ligile, cea mai puternică în Ligue 1, liga cu cele mai multe egaluri. **Ponderile meciurilor recente** au fost alese peste tot, în afară de Serie A.
- **Grilele.** La prima rulare din Faza 15, grila lui $N$ se oprea la trei sezoane de meciuri acasă, iar Premier League și Bundesliga își alegeau chiar valoarea maximă; grila a fost extinsă la cinci sezoane. La prima rulare din Faza 23, La Liga și Bundesliga au ales $K = 10$, cea mai mică valoare a grilei de atunci, iar Bundesliga $h$ = două sezoane, cea mai mare; grilele au primit $K = 5$ și $h$ = patru sezoane, iar valorile alese nu s-au schimbat și nu mai sunt la margine.
- **Valorile diferă destul de mult între ligi**, ceea ce justifică o calibrare separată pentru fiecare.

## 3. Caracterul ligilor

Pe meciurile de evaluare (2010/11–2025/26). „Marja” este diferența medie de goluri în favoarea gazdelor. Sezonul 2020/21 s-a jucat în cea mai mare parte fără spectatori în toate cele cinci ligi.

| Ligă | Victorii gazde | Egaluri | Victorii oaspeți | Goluri pe meci | Marja gazdelor | Victorii gazde în 2020/21 | Victorii gazde în celelalte sezoane |
|---|---|---|---|---|---|---|---|
| Premier League | 44,7% | 24,2% | 31,0% | 2,80 | +0,31 | 37,9% | 45,2% |
| La Liga | 46,6% | 25,0% | 28,3% | 2,67 | +0,41 | 41,6% | 47,0% |
| Serie A | 43,3% | 26,0% | 30,8% | 2,70 | +0,27 | 40,8% | 43,4% |
| Bundesliga | 44,7% | 24,4% | 30,9% | 3,03 | +0,35 | 42,2% | 44,9% |
| Ligue 1 | 44,2% | 26,5% | 29,3% | 2,63 | +0,33 | 37,4% | 44,7% |

- **Bundesliga** are cele mai multe goluri (3,03 pe meci), **Ligue 1** cele mai puține (2,63) și cele mai multe egaluri (26,5%).
- **La Liga** are cel mai mare avantaj al gazdelor: cele mai multe victorii acasă (46,6%) și cea mai mare marjă (+0,41 goluri).
- **Fără spectatori**, victoriile gazdelor au scăzut în toate ligile: cu peste 7 puncte procentuale în Premier League (de la 45,2% la 37,9%) și în Ligue 1 (de la 44,7% la 37,4%), cu aproximativ 5 în La Liga și cu mai puțin de 3 în Bundesliga și Serie A.

## 4. Modelele în fiecare ligă

Acuratețe / scor Brier / pierdere logaritmică. Abilitatea (scorul de abilitate Brier) este $1 - \text{Brier}_{\text{model}} / \text{Brier}_{\text{frecvențele trecute}}$: partea din eroarea referinței pe care modelul o elimină. Ea permite compararea ligilor, chiar dacă unele sunt mai greu de prezis decât altele.

| Ligă | Elo | Poisson | Regresie logistică | Frecvențele trecute | Cel mai bun (Brier) |
|---|---|---|---|---|---|
| Premier League | 53,5% / 0,5866 / 0,9943 | 52,7% / 0,5853 / 0,9837 | 53,5% / 0,5804 / 0,9769 | 44,6% / 0,6459 / 1,0681 | regresia logistică |
| La Liga | 53,6% / 0,5783 / 0,9765 | 53,2% / 0,5819 / 0,9779 | 53,8% / 0,5762 / 0,9700 | 46,6% / 0,6405 / 1,0613 | regresia logistică |
| Serie A | 52,7% / 0,5924 / 1,0028 | 52,5% / 0,5967 / 0,9993 | 53,8% / 0,5844 / 0,9806 | 43,3% / 0,6514 / 1,0764 | regresia logistică |
| Bundesliga | 50,9% / 0,5983 / 1,0036 | 50,5% / 0,5991 / 1,0033 | 50,8% / 0,5958 / 0,9983 | 44,4% / 0,6474 / 1,0705 | regresia logistică |
| Ligue 1 | 50,1% / 0,6070 / 1,0153 | 49,5% / 0,6135 / 1,0225 | 49,9% / 0,6074 / 1,0136 | 44,0% / 0,6493 / 1,0733 | Elo |

| Ligă | Abilitatea Elo | Abilitatea Poisson | Abilitatea regresiei logistice |
|---|---|---|---|
| Premier League | 0,092 | 0,094 | 0,101 |
| La Liga | 0,097 | 0,092 | 0,100 |
| Serie A | 0,091 | 0,084 | 0,103 |
| Bundesliga | 0,076 | 0,075 | 0,080 |
| Ligue 1 | 0,065 | 0,055 | 0,064 |

- **Ligue 1 este cea mai greu de prezis:** cel mai bun model elimină doar 6,5% din eroarea referinței, față de aproximativ 10% în Premier League, La Liga și Serie A. Este și liga cu cele mai multe egaluri și cele mai puține goluri.
- **Bundesliga** este la mijloc (aproximativ 8%).
- Cele „cel mai bun” din tabel sunt doar cele cu scorul Brier cel mai mic; dacă diferența este reală se vede în secțiunea 5.

## 5. Care model este mai bun, ligă cu ligă

Diferențele medii ale scorului Brier, meci cu meci (primul minus al doilea; o valoare negativă înseamnă că primul model este mai bun), cu intervalul de încredere de 95%. O diferență este reală doar dacă intervalul nu conține 0 (`docs/comparison.md`, secțiunea 2).

| Ligă | Elo − regresie logistică | Elo − Poisson | Regresie logistică − Poisson |
|---|---|---|---|
| Premier League | +0,0061 [+0,0030; +0,0093]: regresia logistică | +0,0013 [−0,0024; +0,0051]: nicio diferență reală | −0,0048 [−0,0066; −0,0030]: regresia logistică |
| La Liga | +0,0021 [−0,0003; +0,0045]: nicio diferență reală | −0,0035 [−0,0071; +0,0001]: nicio diferență reală | −0,0057 [−0,0077; −0,0036]: regresia logistică |
| Serie A | +0,0080 [+0,0051; +0,0110]: regresia logistică | −0,0043 [−0,0087; +0,0001]: nicio diferență reală | −0,0123 [−0,0149; −0,0097]: regresia logistică |
| Bundesliga | +0,0025 [−0,0006; +0,0057]: nicio diferență reală | −0,0008 [−0,0043; +0,0027]: nicio diferență reală | −0,0033 [−0,0059; −0,0006]: regresia logistică |
| Ligue 1 | −0,0004 [−0,0026; +0,0018]: nicio diferență reală | −0,0065 [−0,0102; −0,0028]: Elo | −0,0061 [−0,0083; −0,0038]: regresia logistică |
| **Toate ligile (28.893 de meciuri)** | **+0,0038 [+0,0025; +0,0050]: regresia logistică** | **−0,0028 [−0,0045; −0,0011]: Elo** | **−0,0066 [−0,0076; −0,0055]: regresia logistică** |

- **Pe toate ligile la un loc, ordinea este clară și reală:** regresia logistică > Elo > Poisson.
- **Regresia logistică este real mai bună decât Elo în Premier League și Serie A.** În La Liga, Bundesliga și Ligue 1 cele două sunt la egalitate. Am testat doar dacă diferența există, nu de ce apare.
- **Modelul Poisson este real în urma regresiei logistice în toate cele cinci ligi**, dar în urma lui Elo doar în Ligue 1 (înainte de Faza 23, în patru ligi).
- **Toate trei modelele sunt clar mai bune decât frecvențele trecute în fiecare ligă** (secțiunea 4).
- Concluzia din La Liga („regresia logistică ≥ Elo ≈ Poisson”) se păstrează în Bundesliga; în Premier League și Serie A regresia logistică este real mai bună și decât Elo, iar în Ligue 1 Elo este real mai bun decât Poisson.

### 5.1. Ce a schimbat Faza 23

Diferența scorului Brier, meci cu meci, între predicțiile cu setările din Faza 23 și cele de dinainte (rularea din 2026-10-05), cu intervalul de 95%; o valoare negativă înseamnă o îmbunătățire:

| Ligă | Elo | Poisson | Regresie logistică |
|---|---|---|---|
| Premier League | +0,0008 [−0,0008; +0,0024] | −0,0043 [−0,0063; −0,0023] | +0,0014 [+0,0003; +0,0024] |
| La Liga | +0,0007 [−0,0004; +0,0019] | −0,0008 [−0,0024; +0,0008] | −0,0015 [−0,0024; −0,0005] |
| Serie A | 0 (neschimbat) | −0,0003 [−0,0008; +0,0002] | −0,0006 [−0,0012; +0,0000] |
| Bundesliga | +0,0010 [−0,0005; +0,0024] | −0,0030 [−0,0042; −0,0019] | −0,0004 [−0,0008; −0,0001] |
| Ligue 1 | 0 (neschimbat) | −0,0011 [−0,0024; +0,0001] | 0 (neschimbat) |
| **Toate ligile** | **+0,0005 [+0,0000; +0,0010]** | **−0,0019 [−0,0025; −0,0013]** | **−0,0002 [−0,0005; +0,0001]** |

- **Poisson** s-a îmbunătățit real, mai ales în Premier League și Bundesliga, datorită ponderilor meciurilor recente (corecția Dixon–Coles a adus mai puțin, `docs/algorithms/poisson.md`, secțiunea 7.3).
- **Regresia logistică** nu s-a schimbat real pe toate ligile la un loc: e real mai bună în La Liga și Bundesliga și real mai slabă în Premier League.
- **Elo** cu ponderea diferenței de goluri a ajutat pe sezoanele de calibrare, dar nu și pe cele de evaluare (+0,0005, la limita unei înrăutățiri reale).
- Toate schimbările sunt mici, cu un ordin de mărime sub diferența dintre modele și referințe (aproximativ 0,06). Opțiunile au rămas cele alese de calibrare; alegerea lor după aceste rezultate ar fi însemnat calibrare pe perioada raportată.

## 6. Față de casele de pariuri

Fiecare model, comparat cu probabilitățile din media cotelor caselor de pariuri, fără marja lor (metoda: `docs/evaluation.md`, secțiunea 3.4). Cotele sunt doar un reper: nu intră în niciun model. Toate meciurile de evaluare au cote, în afară de unul din Serie A (28.892 din 28.893).

| Ligă | Casele de pariuri (acuratețe / Brier / pierdere logaritmică) | Elo − case | Poisson − case | Regresie logistică − case | Frecvențele trecute − case |
|---|---|---|---|---|---|
| Premier League | 54,6% / 0,5712 / 0,9634 | +0,0153 | +0,0140 | +0,0092 | +0,0746 |
| La Liga | 54,6% / 0,5660 / 0,9547 | +0,0123 | +0,0158 | +0,0102 | +0,0745 |
| Serie A | 54,5% / 0,5711 / 0,9611 | +0,0214 | +0,0256 | +0,0133 | +0,0803 |
| Bundesliga | 52,0% / 0,5855 / 0,9833 | +0,0128 | +0,0136 | +0,0103 | +0,0619 |
| Ligue 1 | 51,8% / 0,5926 / 0,9919 | +0,0145 | +0,0209 | +0,0148 | +0,0567 |
| **Toate ligile** | **53,6% / 0,5768** | **+0,0154 [+0,0139; +0,0169]** | **+0,0181 [+0,0166; +0,0197]** | **+0,0116 [+0,0104; +0,0128]** | **+0,0701 [+0,0670; +0,0732]** |

Coloanele „− case” sunt diferențele medii ale scorului Brier, meci cu meci; toate sunt reale (intervalele lor de 95% sunt departe de 0), deci casele de pariuri prezic mai bine decât fiecare model, în fiecare ligă. Distanța rămasă este însă mică față de cea parcursă: de la frecvențele trecute până la casele de pariuri sunt 0,057–0,080 la scorul Brier, iar cel mai bun model parcurge 74–88% din ea (Premier League 88%, La Liga 86%, Serie A 83%, Bundesliga 83%, Ligue 1 74%). Acuratețea modelelor este cu 0,8–1,7 puncte procentuale sub cea a caselor de pariuri.

## 7. Când modelul e sigur

Acuratețea pe meciurile în care cea mai mare probabilitate a modelului era cel puțin 65%, și numărul acestor meciuri:

| Ligă | Elo | Poisson | Regresie logistică | Casele de pariuri |
|---|---|---|---|---|
| Premier League | 70,1% din 1.820 | 75,1% din 955 | 76,3% din 1.007 | 75,6% din 1.313 |
| La Liga | 72,3% din 1.764 | 79,6% din 749 | 77,0% din 1.201 | 79,4% din 1.163 |
| Serie A | 68,7% din 1.618 | 79,0% din 333 | 73,9% din 1.008 | 75,4% din 1.119 |
| Bundesliga | 71,6% din 1.033 | 76,6% din 556 | 75,9% din 526 | 75,8% din 893 |
| Ligue 1 | 69,4% din 733 | 81,9% din 149 | 78,1% din 407 | 75,4% din 751 |
| **Toate ligile** | **70,5% din 6.968 (24%)** | **77,5% din 2.742 (9%)** | **76,0% din 4.149 (14%)** | **76,4% din 5.239 (18%)** |

Pe toate meciurile, cel mai bun model nimerește 52,4% (regresia logistică, pe toate ligile la un loc) și casele de pariuri 53,6%; pe meciurile în care sunt sigure, toate trec de 70%. Peste 70%, regresia logistică nimerește 79,6% din 2.345 de meciuri (8%), iar casele de pariuri 79,3% din 3.389 (12%). O precizie de peste 70% se poate deci obține, dar doar pe o parte din meciuri: cu cât pragul e mai mare, cu atât sunt mai puține. Poisson are cea mai mare precizie peste prag, dar și cele mai puține meciuri, pentru că e cel mai prudent; Elo e sigur pe cele mai multe meciuri și greșește mai des (`docs/evaluation.md`, secțiunea 3.3).

## 8. Limitări

- Fiecare ligă are un singur set de hiperparametri, ales pe doar trei sezoane (aproximativ 900–1.140 de meciuri). Grilele din Faza 23 au multe alegeri (144 la Elo, 3.696 la Poisson, 20 la regresia logistică), iar diferențele mici dintre ele pot fi întâmplătoare: ponderea golurilor la Elo a ajutat pe calibrare, dar nu și pe evaluare (secțiunea 5.1).
- Multe comparații simultane (cinci ligi, trei perechi) cresc șansa ca o diferență să pară reală întâmplător; diferențele pe toate ligile la un loc au însă intervale departe de 0.
- Sezoanele 2019/20 și 2020/21 au fost afectate de pandemie (meciuri fără spectatori, Ligue 1 2019/20 oprit); sunt păstrate în date și discutate, nu eliminate.
- Clasamentele din aplicație se calculează doar din rezultate: deducerile oficiale de puncte și regulile de departajare ale fiecărei ligi nu sunt modelate.
- Numele echipelor sunt cele din fișierele sursă (de exemplu `Man United`, `Nott'm Forest`, `Ath Madrid`).

## 9. Reproducere

```bash
python -m app.data.build_database
python -m app.evaluation.league_calibration
python -m app.evaluation.backtesting
python -m app.evaluation.leagues
python -m app.evaluation.bookmakers
```

Pentru o singură ligă: `python -m app.evaluation.evaluator E0` și `python -m app.evaluation.comparison E0`.
