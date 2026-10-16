# Ratingul Elo

Acest document descrie implementarea noastră a sistemului Elo din `app/algorithms/elo.py` și felul în care este folosit în PitchSense. Ecuațiile sunt numerotate la fel ca în cod.

## 1. Problema rezolvată

Elo estimează forța relativă a echipelor. Fiecare echipă are un rating, un singur număr care se actualizează după fiecare meci. Din diferența de rating dintre două echipe rezultă scorul așteptat al unui meci. Modelul egalurilor transformă apoi acest scor în probabilitățile celor trei rezultate posibile: victoria gazdelor, egal, victoria oaspeților.

## 2. De ce este potrivit

- Folosește doar rezultatele meciurilor, care există pentru toate cele 20 de sezoane.
- Se actualizează meci cu meci, în ordine cronologică. Ratingul de dinaintea unui meci depinde deci doar de meciurile anterioare, exact ce cere evaluarea fără scurgere de informații.
- Ține cont de puterea adversarului: o victorie cu o echipă puternică aduce mai multe puncte decât una cu o echipă slabă.
- Are puțini parametri (K, H și, din Faza 23, alegerea de a ține cont de diferența de goluri), ușor de interpretat și de calibrat.
- Este rapid: actualizarea după un meci costă O(1).

## 3. Principiul matematic

Notații: $R_h$ și $R_a$ sunt ratingurile gazdelor și oaspeților înaintea meciului, $H$ este avantajul terenului propriu (în puncte de rating), iar $K$ este factorul de actualizare.

**Scorul așteptat al gazdelor (Ec. 1):**

$$E_h = \frac{1}{1 + 10^{(R_a - R_h - H)/400}}$$

Pentru oaspeți, $E_a = 1 - E_h$. O diferență de 400 de puncte înseamnă un scor așteptat de 10/11 pentru echipa mai puternică.

**Scorul real al gazdelor (Ec. 2):** $S_h = 1$ pentru victorie, $0{,}5$ pentru egal și $0$ pentru înfrângere.

**Actualizarea (Ec. 3):**

$$\Delta = K\,G\,(S_h - E_h), \qquad R_h' = R_h + \Delta, \qquad R_a' = R_a - \Delta$$

Gazdele câștigă exact câte puncte pierd oaspeții, deci suma ratingurilor din ligă rămâne constantă.

**Ponderea diferenței de goluri (Ec. 7, Faza 23).** Fără ea, $G = 1$ și o victorie cu 5–0 valorează cât una cu 1–0. Cu ea, pentru diferența $N = |\text{goluri}_h - \text{goluri}_a|$:

$$G = \begin{cases} 1, & N \le 1 \\ 1{,}5, & N = 2 \\ (11 + N)/8, & N \ge 3 \end{cases}$$

adică formula World Football Elo Ratings (eloratings.net): 1,75 pentru 3 goluri, 1,875 pentru 4 și așa mai departe. $G$ schimbă doar cât de mult se mișcă ratingurile, nu și în ce direcție (un egal are $N = 0$, deci $G = 1$), iar actualizarea rămâne cu sumă nulă. Folosirea lui $G$ este o opțiune aleasă de calibrare pentru fiecare ligă (secțiunea 7.3).

**Începutul sezoanelor.** În primul sezon toate echipele pornesc de la 1500. La începutul fiecărui sezon următor:

- echipele care rămân în ligă își păstrează ratingul (fără regresie spre medie);
- echipele care au plecat sunt eliminate;
- echipele care intră (promovate sau revenite după o absență) primesc media ratingurilor echipelor care au plecat. Când intră tot atâtea echipe câte au plecat, suma și media ratingurilor rămân neschimbate.

**De la scorul așteptat la cele trei probabilități.** $E_h$ nu este probabilitatea victoriei: un egal contează jumătate de victorie, deci $E_h = P(H) + P(D)/2$. Modelul egalurilor estimează $P(D)$ din meciurile anterioare:

- **Ec. 4:** intervalul $[0, 1]$ al lui $E$ este împărțit în $B$ coșuri egale; coșul lui $E$ este $b(E) = \min(\lfloor E \cdot B \rfloor,\ B - 1)$.
- **Ec. 5:** rata egalurilor din coșul $b$ este $d_b = \dfrac{e_b + m\,\bar{d}}{n_b + m}$, unde $n_b$ și $e_b$ sunt numărul de meciuri și de egaluri din coș, $\bar{d}$ este rata generală a egalurilor, iar $m$ este o greutate care trage coșurile cu puține meciuri spre rata generală.
- **Ec. 6:**

$$P(D) = \min\big(d_{b(E)},\ \max(0,\ 2\min(E, 1 - E) - 2q)\big), \qquad P(H) = E - \frac{P(D)}{2}, \qquad P(A) = 1 - E - \frac{P(D)}{2}$$

unde $q = 0{,}01$ este probabilitatea minimă păstrată de fiecare victorie. Limita garantează că nicio probabilitate nu este negativă și că, pentru $q \le E \le 1 - q$, ambele victorii au cel puțin 1%; strict între aceste limite și egalul are o probabilitate pozitivă. Astfel, niciun rezultat posibil nu este declarat imposibil. Cele trei probabilități au suma 1 și păstrează exact scorul așteptat Elo.

## 4. Intrări

- parametrii $K$ și $H$, alegerea ponderii diferenței de goluri și ratingul inițial (1500);
- lista echipelor fiecărui sezon, cunoscută înainte de începerea sezonului;
- meciurile, în ordine cronologică: data, gazdele, oaspeții și golurile fiecărei echipe (`GameResult`);
- pentru modelul egalurilor: perechi $(E_h, S_h)$ din meciuri anterioare și parametrii $B$ și $m$.

## 5. Ieșiri

- ratingul curent al fiecărei echipe și ratingurile de dinaintea fiecărui meci;
- scorul așteptat $E_h$ al fiecărui meci;
- probabilitățile $(P(H), P(D), P(A))$, în această ordine, în formatul comun al predicțiilor.

## 6. Pseudocod

```
ELO(meciuri, K, H, cu_goluri):
    R ← dicționar gol                                 ▷ ratingurile echipelor
    pentru fiecare zi D, în ordine cronologică:
        dacă în ziua D începe un sezon nou s:
            ÎNCEPE_SEZON(R, echipele sezonului s)
        pentru fiecare meci (g, o) din ziua D:         ▷ întâi predicțiile zilei
            E[g, o] ← 1 / (1 + 10^((R[o] − R[g] − H) / 400))
        pentru fiecare meci (g, o, goluri_g, goluri_o) din ziua D:   ▷ apoi rezultatele
            S ← 1 dacă goluri_g > goluri_o; 0,5 dacă goluri_g = goluri_o; altfel 0
            G ← PONDERE(|goluri_g − goluri_o|) dacă cu_goluri, altfel 1
            Δ ← K · G · (S − E[g, o])
            R[g] ← R[g] + Δ
            R[o] ← R[o] − Δ
    returnează E, R

ÎNCEPE_SEZON(R, echipe):
    dacă R este gol:
        R[e] ← 1500 pentru fiecare e din echipe
        returnează
    plecate ← echipele din R care nu sunt în echipe
    r_intrare ← media lui R[p] pentru p din plecate
                (sau media tuturor ratingurilor, dacă nu a plecat nimeni)
    R ← { e : R[e] dacă e era deja în R, altfel r_intrare   pentru e din echipe }

PONDERE(N):                                          ▷ Ec. 7
    dacă N ≤ 1: returnează 1
    dacă N = 2: returnează 1,5
    returnează (11 + N) / 8

PROBABILITĂȚI(E, d, B):                               ▷ d = ratele egalurilor pe coșuri
    p_D ← min(d[min(⌊E · B⌋, B − 1)], max(0, 2 · min(E, 1 − E) − 2 · q))   ▷ q = 0,01
    returnează (E − p_D / 2, p_D, 1 − E − p_D / 2)
```

## 7. Detalii de implementare

### 7.1. Fișiere

| Fișier | Conținut |
|---|---|
| `app/algorithms/elo.py` | Ec. 1–7: formulele (`margin_weight` pentru Ec. 7), `EloRatings` (ratingurile, actualizarea, începutul sezoanelor; `goal_margin` alege Ec. 7) și `DrawModel` (modelul egalurilor). Folosește doar biblioteca standard Python. |
| `app/prediction/elo_predictions.py` | `run_elo`: rulează Elo pe meciurile unei competiții, zi cu zi; parametrii aleși sunt valorile implicite. |
| `app/evaluation/elo_calibration.py` | Alegerea lui K, H și a ponderii golurilor: `python -m app.evaluation.elo_calibration`. |
| `app/evaluation/periods.py` | Sezoanele de încălzire, de calibrare și de evaluare. |

Toate meciurile unei zile sunt prezise înainte să se aplice vreun rezultat din acea zi. Meciurile care nu sunt în ordine cronologică, o echipă necunoscută sau parametrii invalizi ($K \le 0$, $H < 0$) produc o eroare.

### 7.2. Valorile parametrilor

| Parametru | Valoare | Cum a fost ales |
|---|---|---|
| $K$ | 10 | calibrare (secțiunea 7.3) |
| $H$ | 80 | calibrare (secțiunea 7.3) |
| ponderea diferenței de goluri (Ec. 7) | da | calibrare (secțiunea 7.3), din Faza 23 |
| ratingul inițial | 1500 | convenția uzuală Elo |
| $B$ (coșuri) | 10 | valoare implicită documentată |
| $m$ (greutate) | 20 | valoare implicită documentată |
| $q$ (probabilitatea minimă a unei victorii) | 0,01 | adăugată în Faza 9 (secțiunea 7.5) |

Valorile sunt cele ale La Liga. Fiecare ligă are valorile ei, alese cu aceeași grilă pe propriile sezoane de calibrare (rulare din 2026-10-16): Premier League $K = 15$, $H = 80$, cu ponderea golurilor; Serie A $K = 20$, $H = 100$, fără; Bundesliga $K = 10$, $H = 60$, cu; Ligue 1 $K = 15$, $H = 60$, fără (`docs/leagues.md`, secțiunea 2). Ponderea golurilor înmulțește $K$ cu $G \ge 1$, de aceea ligile care o folosesc au ales un $K$ mai mic decât înainte (La Liga 15 → 10, Premier League 25 → 15, Bundesliga 15 → 10).

### 7.3. Calibrarea lui K, H și a ponderii golurilor

Elo a fost rulat doar pe sezonul de încălzire 2006/07 și pe sezoanele de calibrare 2007/08–2009/10; sezoanele de evaluare nu sunt citite. Pentru fiecare dintre cele 144 de alegeri ale grilei ($K \in \{5, 10, 15, \ldots, 40\}$, $H \in \{0, 20, \ldots, 160\}$, cu sau fără ponderea golurilor) s-a calculat eroarea pătratică medie dintre $S_h$ și $E_h$ pe cele 1.140 de meciuri de calibrare. Ponderea golurilor este deci o alegere în plus a aceleiași grile: e folosită doar acolo unde prezice mai bine sezoanele de calibrare. Rulare din 2026-10-16:

| K | H | Ponderea golurilor | Eroarea pătratică medie |
|---|---|---|---|
| **10** | **80** | **da** | **0,15946** |
| 15 | 80 | da | 0,15988 |
| 10 | 100 | da | 0,16003 |
| 15 | 100 | da | 0,16021 |
| 10 | 60 | da | 0,16025 |
| 15 | 80 | nu | 0,16034 |

Ultimul rând este alegerea de până în Faza 23 ($K = 15$, $H = 80$, fără ponderea golurilor). Ca referință, o predicție constantă, fără ratinguri (media scorului real al gazdelor din 2006/07), are eroarea 0,18101; Elo o reduce cu 11,9%. Valoarea $K = 5$ a fost adăugată grilei în Faza 23, după ce prima rulare a ales pentru La Liga și Bundesliga $K = 10$, cea mai mică valoare de atunci; cu ea, valorile alese sunt în interiorul grilei.

Cu $H = 80$, pentru două echipe egale $E_h = 0{,}6131$. Pe sezoanele de calibrare, media lui $E_h$ este 0,6045, iar media scorului real al gazdelor este 0,6075, deci avantajul terenului propriu este estimat corect.

### 7.4. Modelul egalurilor pe sezoanele de calibrare

Modelul potrivit pe cele 1.140 de meciuri de calibrare, cu $K = 10$, $H = 80$ și ponderea golurilor:

| $E_h$ | Meciuri | Rata egalurilor $d_b$ |
|---|---|---|
| 0,0–0,2 | 0 | 0,232 (rata generală) |
| 0,2–0,3 | 22 | 0,254 |
| 0,3–0,4 | 70 | 0,229 |
| 0,4–0,5 | 148 | 0,236 |
| 0,5–0,6 | 279 | 0,263 |
| 0,6–0,7 | 350 | 0,275 |
| 0,7–0,8 | 203 | 0,169 |
| 0,8–0,9 | 65 | 0,102 |
| 0,9–1,0 | 3 | 0,202 |

Egalurile sunt mai frecvente între echipe apropiate ca forță ($E_h$ între 0,5 și 0,7) și rare când o echipă este clar favorită. De exemplu, pentru două echipe egale ($E_h = 0{,}6131$) probabilitățile sunt 0,476 / 0,275 / 0,249. În evaluarea cronologică (Faza 8), modelul este potrivit de fiecare dată doar pe meciurile anterioare.

### 7.5. Modificare în Faza 9: probabilitatea minimă

Inițial, Ec. 6 limita egalul la $2\min(E, 1 - E)$. Pentru meciuri foarte dezechilibrate, limita era atinsă exact, iar victoria echipei slabe primea probabilitatea 0. Evaluarea (Faza 9) a găsit 6 astfel de predicții din 6.080. Într-una dintre ele, Barcelona – Hércules (0–2, 11 septembrie 2010), echipa slabă a câștigat, iar pierderea logaritmică a modelului a devenit infinită.

Echipa a ales să corecteze modelul: limita a devenit $2\min(E, 1 - E) - 2q$, cu $q = 0{,}01$, deci fiecare victorie păstrează cel puțin 1%. Corecția a schimbat doar 15 din cele 6.080 de predicții de evaluare (0,25%) și nu a modificat $K$, $H$ sau modelul egalurilor. Pentru meciul de mai sus, Elo a prezis atunci 83,7% / 15,3% / 1,0%; cu setările din Faza 23 prezice 86,1% / 12,9% / 1,0%. Detalii în `docs/evaluation.md`, secțiunea 5.

### 7.6. Modificare în Faza 23: diferența de goluri

Echipa a cerut ca Elo să țină cont de diferența de goluri. Ec. 7 a fost adăugată ca opțiune a grilei de calibrare, nu impusă: calibrarea a ales-o pentru Premier League, La Liga și Bundesliga, nu și pentru Serie A și Ligue 1, unde Elo a rămas neschimbat. Pe sezoanele de evaluare (2010/11–2025/26), comparat meci cu meci cu Elo de dinainte, scorul Brier al celor trei ligi s-a schimbat cu +0,0008 (Premier League), +0,0007 (La Liga) și +0,0010 (Bundesliga), niciuna o diferență reală (intervalele de 95% conțin 0). Pe toate cele cinci ligi la un loc, diferența este +0,0005, cu intervalul [+0,0000; +0,0010], la limita unei înrăutățiri reale. Cu alte cuvinte, ponderea golurilor a ajutat pe cele trei sezoane de calibrare (eroarea pătratică 0,15946 față de 0,16034 în La Liga), dar nu și pe cele 16 sezoane de evaluare. Valorile au rămas cele alese de calibrare: alegerea lor după rezultatele de evaluare ar fi însemnat calibrare pe perioada raportată (`docs/evaluation.md`).

## 8. Complexitate

Notații: $n$ — numărul de meciuri, $t$ — numărul de echipe dintr-un sezon, $B$ — numărul de coșuri, $g$ — numărul de perechi din grila de calibrare, $n_c$ — numărul de meciuri din sezoanele de încălzire și calibrare.

| Operație | Timp | Memorie |
|---|---|---|
| Scorul așteptat și actualizarea după un meci | O(1) | O(1) |
| Începutul unui sezon | O(t) | O(t) |
| Rularea pe tot istoricul (`run_elo`) | O(n log n) pentru sortare + O(n) | O(t) pentru ratinguri + O(n) pentru predicțiile salvate |
| Potrivirea modelului egalurilor | O(n + B) | O(B) |
| Probabilitățile unui meci | O(1) | O(1) |
| Calibrarea | O(g · n_c log n_c) | O(n_c) |

Dacă meciurile sunt deja sortate (cum le întoarce baza de date), rularea pe tot istoricul este practic liniară.

## 9. Ipoteze

- Forța unei echipe poate fi descrisă printr-un singur număr, care se schimbă treptat.
- Avantajul terenului propriu este același pentru toate echipele și toate sezoanele.
- Fără ponderea golurilor (Serie A, Ligue 1) contează doar rezultatul, nu scorul: o victorie cu 5–0 valorează cât una cu 1–0. Cu ea, diferența de goluri spune ceva în plus despre forța echipelor, după formula fixă din Ec. 7.
- Diferența de rating determină scorul așteptat prin curba din Ec. 1 (bază 10, scală 400).
- Probabilitatea egalului depinde doar de scorul așteptat $E_h$.

## 10. Limitări

- Echipele nou promovate pornesc de la media echipelor retrogradate, fără informații despre lotul lor. În primul sezon toate echipele pornesc egal; de aceea sezonul 2006/07 este folosit doar pentru încălzire.
- Nu ține cont de accidentări, transferuri, calendar sau motivație; în Serie A și Ligue 1 nici de diferența de goluri.
- Formula lui $G$ este fixă, luată de la World Football Elo Ratings (făcută pentru meciurile echipelor naționale), nu potrivită pe datele noastre; calibrarea alege doar dacă e folosită.
- $K$ este constant: ratingurile reacționează la fel de repede la începutul și la sfârșitul sezonului.
- $H$ este constant: în sezonul 2020/21, jucat fără spectatori, gazdele au câștigat doar 41,6% dintre meciuri, cel mai puțin din cele 20 de sezoane.
- Ratingurile trec neschimbate de la un sezon la altul, deci schimbările din pauza de vară (transferuri, antrenori) nu sunt reflectate.
- Coșurile extreme ale modelului egalurilor au foarte puține meciuri (0–0,2: niciunul în sezoanele de calibrare) și se bazează pe rata generală.
- Calibrarea folosește doar trei sezoane (1.140 de meciuri).

## 11. Exemple din teste

Testele sunt în `tests/test_elo.py`, `tests/test_elo_predictions.py` și `tests/test_elo_calibration.py`.

- Două echipe de 1500, $H = 0$, $K = 20$: învingătoarea câștigă exact 10 puncte, iar învinsa pierde 10.
- Ponderea golurilor: $G = 1$ pentru 0–0, 1–0 și 0–1, 1,5 pentru 2–0 și 1–3, 1,75 pentru 3–0, 1,875 pentru 0–4 și 2,25 pentru 7–0; cu ea, un 4–0 între echipe de 1500 aduce $10 \cdot 15/8 = 18{,}75$ puncte, un 1–0 tot 10, iar un egal are ponderea 1. Suma ratingurilor rămâne constantă și cu ponderea golurilor.
- Cu $H = 100$: $E_h = 0{,}6401$; o victorie a gazdelor aduce +7,20, iar un egal costă gazdele 2,80 puncte.
- După A–B (1–0) și B–C (3–1): B are 1500,29, iar C are 1489,71.
- Suma ratingurilor rămâne constantă după 200 de meciuri aleatorii și la promovări; o echipă care revine nu își primește înapoi vechiul rating.
- Modelul egalurilor: ratele pe coșuri 1/2 și 2/3 fără greutate, 4/7 și 5/8 cu $m = 5$; pentru $E = 0{,}1$ și o rată de 0,6, limita dă (0,01; 0,18; 0,81), iar pentru $E = 0{,}95$ dă (0,91; 0,08; 0,01): fiecare victorie păstrează 1%.
- Pe 20.000 de meciuri simulate, cu 30% egaluri pentru $E$ între 0,4 și 0,6 și 15% în rest, modelul regăsește aceste rate.
- Calibrarea: eroarea unui singur meci de calibrare este $(1 - 0{,}52875)^2$; după un 3–0 în încălzire, cu ponderea golurilor gazdele câștigă 17,5 puncte, $E_h = 0{,}550199$, iar eroarea este $(1 - 0{,}550199)^2$, mai mică, deci calibrarea alege ponderea golurilor; sezoanele din afara încălzirii și calibrării nu influențează rezultatul.
- Fără scurgere de informații: schimbarea rezultatului unui meci nu modifică nicio predicție din ziua lui sau dinainte, dar modifică predicțiile ulterioare.

## 12. Rolul în PitchSense

- Este primul algoritm de predicție: pentru fiecare meci oferă probabilitățile victorie gazde / egal / victorie oaspeți, care vor fi comparate cu cele ale modelului Poisson și ale regresiei logistice (fazele 8–10).
- Ratingurile în timp sunt afișate în ecranul Echipe, în graficul „Rating Elo” (Faza 12): ratingul echipei înaintea fiecărui meci.
- Diferența de rating, calculată doar din meciurile anterioare, poate deveni o caracteristică pentru regresia logistică (Faza 5).

Verificare pe datele reale (rulare din 2026-10-16, cu $K = 10$, $H = 80$ și ponderea golurilor, pe toate cele 7.600 de meciuri ale La Liga):

- suma ratingurilor rămâne 30.000 (20 × 1500) după toate meciurile;
- echipa cu cel mai mare rating la sfârșitul sezonului are cele mai multe puncte în 15 din 20 de sezoane (în 2006/07, Real Madrid, echipa cu cel mai mare rating, și Barcelona au avut amândouă 76 de puncte). În celelalte cinci (2011/12, 2013/14, 2016/17, 2019/20, 2020/21), Barcelona, cu victoriile ei la scor, are cel mai mare rating, deși campioana a fost Real Madrid sau Atlético Madrid; fără ponderea golurilor erau 16 sezoane;
- după sezonul 2025/26: Barcelona 1781, Real Madrid 1754, Atlético Madrid 1644; ultimele sunt cele trei echipe promovate, Levante 1388, Elche 1385 și Oviedo 1335;
- cele 57 de echipe promovate au câștigat în medie 5,4 puncte de rating în primul lor sezon (de la începutul sezonului până după ultimul lor meci), iar 26 dintre ele au scăzut. Regula de intrare nu le supraevaluează deci sistematic.

## 13. Surse

- Elo, A. E. (1978). *The Rating of Chessplayers, Past and Present*. New York: Arco.
- Hvattum, L. M., & Arntzen, H. (2010). Using ELO ratings for match result prediction in association football. *International Journal of Forecasting*, 26(3), 460–470.
- World Football Elo Ratings, https://www.eloratings.net – un exemplu de aplicare a sistemului Elo în fotbal și sursa ponderii diferenței de goluri (Ec. 7).

Codul a fost scris pornind de la formulele de mai sus, nu copiat dintr-o implementare existentă.

## 14. Reproducere

```bash
python -m app.data.build_database
python -m app.evaluation.elo_calibration
```
