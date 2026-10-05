# Comparația ligilor

Acest document compară cele cinci ligi din PitchSense: cum arată fotbalul în fiecare dintre ele și cât de bine funcționează aceiași algoritmi în fiecare. Toate ligile folosesc aceleași perioade (încălzire 2006/07, calibrare 2007/08–2009/10, evaluare 2010/11–2025/26), aceeași procedură de calibrare și aceleași măsuri (`docs/evaluation.md`). Analiza este făcută de `app/evaluation/leagues.py`. Toate valorile provin din rularea din 2026-10-05.

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

Fiecare ligă își alege hiperparametrii pe propriile sezoane de încălzire și calibrare (`python -m app.evaluation.league_calibration`), cu aceleași grile și aceleași măsuri ca La Liga în fazele 3–5. Ferestrele de „un sezon” urmează mărimea ligii: 380 de meciuri și 19 meciuri acasă pe echipă la 20 de echipe, 306 și 17 la 18 echipe. În paranteză este referința fiecărui model: predicția constantă pentru Elo, mediile ligii pentru Poisson și frecvențele din sezonul de încălzire pentru regresia logistică.

| Ligă | K | H | N | m | L2 | Elo: eroarea pătratică medie | Poisson: media lui $-\ln P(\text{scorul real})$ | Regresie logistică: pierderea logaritmică |
|---|---|---|---|---|---|---|---|---|
| Premier League | 25 | 80 | 76 | 10 | 0,01 | 0,13919 (0,17496) | 2,87981 (3,00502) | 0,94331 (1,05548) |
| La Liga | 15 | 80 | 76 | 20 | 0,1 | 0,16034 (0,18101) | 2,95296 (3,02654) | 0,98627 (1,04696) |
| Serie A | 20 | 100 | 38 | 20 | 0,1 | 0,14982 (0,16792) | 2,80998 (2,86037) | 0,99533 (1,05130) |
| Bundesliga | 15 | 60 | 51 | 20 | 0,1 | 0,16316 (0,17873) | 2,99437 (3,06146) | 1,02318 (1,06817) |
| Ligue 1 | 15 | 60 | 38 | 30 | 0,1 | 0,15589 (0,17204) | 2,74858 (2,78241) | 1,03442 (1,07721) |

- **Avantajul terenului propriu** ales pentru Elo este cel mai mare în Serie A ($H = 100$) și cel mai mic în Bundesliga și Ligue 1 ($H = 60$).
- **Premier League** are cel mai mare $K = 25$: ratingurile se schimbă mai repede după fiecare rezultat. Tot acolo regresia logistică își alege penalizarea cea mai mică ($L2 = 0{,}01$).
- **Grila lui N.** La prima rulare, grila lui $N$ se oprea la trei sezoane de meciuri acasă, iar Premier League și Bundesliga își alegeau chiar valoarea maximă. Grila a fost extinsă la cinci sezoane pentru toate ligile; acum nicio valoare aleasă nu mai este la marginea grilei. Aceeași regulă a mutat și La Liga de la $N = 38$ la $N = 76$ (`docs/algorithms/poisson.md`, secțiunea 7.3). Pentru Premier League și La Liga, $N = 76$ înseamnă, în sezoanele de calibrare, tot istoricul disponibil: calibrarea nu poate deosebi ferestrele mai lungi.
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
| Premier League | 53,4% / 0,5858 / 0,9900 | 51,9% / 0,5896 / 0,9898 | 53,6% / 0,5791 / 0,9752 | 44,6% / 0,6459 / 1,0681 | regresia logistică |
| La Liga | 53,4% / 0,5776 / 0,9735 | 52,6% / 0,5827 / 0,9794 | 53,6% / 0,5777 / 0,9721 | 46,6% / 0,6405 / 1,0613 | Elo |
| Serie A | 52,7% / 0,5924 / 1,0028 | 52,5% / 0,5970 / 1,0004 | 53,6% / 0,5850 / 0,9813 | 43,3% / 0,6514 / 1,0764 | regresia logistică |
| Bundesliga | 50,8% / 0,5973 / 1,0011 | 50,5% / 0,6021 / 1,0079 | 50,9% / 0,5962 / 0,9989 | 44,4% / 0,6474 / 1,0705 | regresia logistică |
| Ligue 1 | 50,1% / 0,6070 / 1,0153 | 49,3% / 0,6147 / 1,0246 | 49,9% / 0,6074 / 1,0136 | 44,0% / 0,6493 / 1,0733 | Elo |

| Ligă | Abilitatea Elo | Abilitatea Poisson | Abilitatea regresiei logistice |
|---|---|---|---|
| Premier League | 0,093 | 0,087 | 0,103 |
| La Liga | 0,098 | 0,090 | 0,098 |
| Serie A | 0,091 | 0,083 | 0,102 |
| Bundesliga | 0,077 | 0,070 | 0,079 |
| Ligue 1 | 0,065 | 0,053 | 0,064 |

- **Ligue 1 este cea mai greu de prezis:** cel mai bun model elimină doar 6,5% din eroarea referinței, față de aproximativ 10% în Premier League, La Liga și Serie A. Este și liga cu cele mai multe egaluri și cele mai puține goluri.
- **Bundesliga** este la mijloc (aproximativ 8%).
- Cele „cel mai bun” din tabel sunt doar cele cu scorul Brier cel mai mic; dacă diferența este reală se vede în secțiunea 5.

## 5. Care model este mai bun, ligă cu ligă

Diferențele medii ale scorului Brier, meci cu meci (primul minus al doilea; o valoare negativă înseamnă că primul model este mai bun), cu intervalul de încredere de 95%. O diferență este reală doar dacă intervalul nu conține 0 (`docs/comparison.md`, secțiunea 2).

| Ligă | Elo − regresie logistică | Elo − Poisson | Regresie logistică − Poisson |
|---|---|---|---|
| Premier League | +0,0067 [+0,0041; +0,0093]: regresia logistică | −0,0038 [−0,0079; +0,0004]: nicio diferență reală | −0,0105 [−0,0139; −0,0070]: regresia logistică |
| La Liga | −0,0001 [−0,0023; +0,0022]: nicio diferență reală | −0,0051 [−0,0083; −0,0019]: Elo | −0,0050 [−0,0078; −0,0023]: regresia logistică |
| Serie A | +0,0074 [+0,0045; +0,0104]: regresia logistică | −0,0046 [−0,0089; −0,0003]: Elo | −0,0120 [−0,0149; −0,0092]: regresia logistică |
| Bundesliga | +0,0011 [−0,0015; +0,0037]: nicio diferență reală | −0,0047 [−0,0082; −0,0013]: Elo | −0,0059 [−0,0089; −0,0029]: regresia logistică |
| Ligue 1 | −0,0004 [−0,0026; +0,0018]: nicio diferență reală | −0,0076 [−0,0113; −0,0039]: Elo | −0,0072 [−0,0098; −0,0047]: regresia logistică |
| **Toate ligile (28.893 de meciuri)** | **+0,0031 [+0,0019; +0,0042]: regresia logistică** | **−0,0052 [−0,0069; −0,0034]: Elo** | **−0,0082 [−0,0096; −0,0069]: regresia logistică** |

- **Pe toate ligile la un loc, ordinea este clară și reală:** regresia logistică > Elo > Poisson.
- **Regresia logistică este real mai bună decât Elo în Premier League și Serie A.** În La Liga, Bundesliga și Ligue 1 cele două sunt la egalitate. Am testat doar dacă diferența există, nu de ce apare.
- **Modelul Poisson este real în urma regresiei logistice în toate cele cinci ligi** și în urma lui Elo în patru dintre ele; în Premier League diferența față de Elo nu este reală.
- **Toate trei modelele sunt clar mai bune decât frecvențele trecute în fiecare ligă** (secțiunea 4).
- Concluzia din La Liga („Elo ≈ regresia logistică > Poisson”) se păstrează în ligile mai greu de prezis, dar nu și în Premier League și Serie A, unde indicatorii adăugați peste diferența Elo aduc o îmbunătățire măsurabilă.

## 6. Limitări

- Fiecare ligă are un singur set de hiperparametri, ales pe doar trei sezoane (aproximativ 900–1.140 de meciuri).
- Multe comparații simultane (cinci ligi, trei perechi) cresc șansa ca o diferență să pară reală întâmplător; diferențele pe toate ligile la un loc au însă intervale departe de 0.
- Sezoanele 2019/20 și 2020/21 au fost afectate de pandemie (meciuri fără spectatori, Ligue 1 2019/20 oprit); sunt păstrate în date și discutate, nu eliminate.
- Clasamentele din aplicație se calculează doar din rezultate: deducerile oficiale de puncte și regulile de departajare ale fiecărei ligi nu sunt modelate.
- Numele echipelor sunt cele din fișierele sursă (de exemplu `Man United`, `Nott'm Forest`, `Ath Madrid`).

## 7. Reproducere

```bash
python -m app.data.build_database
python -m app.evaluation.league_calibration
python -m app.evaluation.backtesting
python -m app.evaluation.leagues
```

Pentru o singură ligă: `python -m app.evaluation.evaluator E0` și `python -m app.evaluation.comparison E0`.
