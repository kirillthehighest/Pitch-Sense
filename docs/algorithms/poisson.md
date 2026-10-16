# Modelul Poisson

Acest document descrie implementarea noastră a modelului Poisson din `app/algorithms/poisson.py` și felul în care este folosit în PitchSense. Ecuațiile sunt numerotate la fel ca în cod.

## 1. Problema rezolvată

Modelul Poisson estimează câte goluri va marca fiecare echipă într-un meci și calculează probabilitatea fiecărui scor posibil (0–0, 1–0, 2–1 și așa mai departe). Din tabelul scorurilor rezultă probabilitățile victoriei gazdelor, egalului și victoriei oaspeților. Spre deosebire de Elo, modelul prezice scorul, nu doar rezultatul.

## 2. De ce este potrivit

- Golurile sunt evenimente rare și relativ independente într-un meci, iar numărul lor este bine descris de o distribuție Poisson.
- Distribuția Poisson are un singur parametru, media $\lambda$, care se poate estima simplu din golurile marcate și primite anterior.
- Oferă mai mult decât un rezultat: numărul așteptat de goluri, scorurile cele mai probabile și probabilitățile celor trei rezultate.
- Calculul este rapid: tabelul scorurilor are doar $(G+1)^2$ celule.

## 3. Principiul matematic

**Probabilitatea a $k$ goluri (Ec. 1).** Dacă o echipă marchează în medie $\lambda$ goluri,

$$P(k;\lambda) = \frac{\lambda^k e^{-\lambda}}{k!}$$

În cod, valorile se calculează prin recurența $P(0) = e^{-\lambda}$ și $P(k) = P(k-1) \cdot \lambda / k$, care evită numerele foarte mari $\lambda^k$ și $k!$.

**Probabilitatea unui scor (Ec. 2).** Presupunând că golurile celor două echipe sunt independente,

$$P(i, j) = P(i;\lambda_h) \cdot P(j;\lambda_a)$$

unde $\lambda_h$ și $\lambda_a$ sunt golurile așteptate ale gazdelor și oaspeților. Tabelul păstrează scorurile până la $G$ goluri pentru fiecare echipă. Probabilitatea scorurilor mai mari este raportată separat și tabelul este rescalat la suma 1.

**Cele trei rezultate (Ec. 3):**

$$P(H) = \sum_{i > j} P(i, j), \qquad P(D) = \sum_{i} P(i, i), \qquad P(A) = \sum_{i < j} P(i, j)$$

**Forța unei echipe (Ec. 4).** Forța este numărul de goluri pe meci raportat la media ligii $\mu$, trasă spre 1 (o echipă medie) cu $m$ meciuri imaginare de nivel mediu:

$$\text{forța} = \frac{(\text{goluri} + m\,\mu) / (\text{meciuri} + m)}{\mu}$$

Pentru atac se folosesc golurile marcate, iar pentru apărare golurile primite: o valoare peste 1 înseamnă o apărare mai slabă decât media. Fără niciun meci anterior, forța este exact 1. Cu ponderile din Ec. 7, „goluri” și „meciuri” sunt sumele ponderate.

**Golurile așteptate (Ec. 5).** Cu $\mu_h$ și $\mu_a$ media golurilor gazdelor și oaspeților în ligă:

$$\lambda_h = \text{atac}_{\text{gazde, acasă}} \cdot \text{apărare}_{\text{oaspeți, deplasare}} \cdot \mu_h, \qquad \lambda_a = \text{atac}_{\text{oaspeți, deplasare}} \cdot \text{apărare}_{\text{gazde, acasă}} \cdot \mu_a$$

Forța gazdelor se calculează doar din meciurile lor de acasă, iar cea a oaspeților doar din meciurile lor din deplasare.

**Corecția Dixon–Coles a scorurilor mici (Ec. 6, Faza 23).** Socotite independent, golurile celor două echipe dau de obicei prea puține egaluri, mai ales 0–0 și 1–1 (Dixon și Coles, 1997). Corecția înmulțește cele patru scoruri mici cu

$$\tau(0,0) = 1 - \lambda_h \lambda_a \rho, \quad \tau(0,1) = 1 + \lambda_h \rho, \quad \tau(1,0) = 1 + \lambda_a \rho, \quad \tau(1,1) = 1 - \rho$$

și lasă celelalte scoruri neschimbate ($\tau = 1$). Cu $\rho < 0$, 0–0 și 1–1 primesc exact cât pierd 1–0 și 0–1: cele patru schimbări sunt $e^{-\lambda_h - \lambda_a} \lambda_h \lambda_a \rho \cdot (-1 + 1 + 1 - 1) = 0$, deci suma tabelului și golurile așteptate ale ambelor echipe rămân aceleași. Dixon și Coles cer doar ca niciun $\tau$ să nu fie negativ. La noi însă $\rho$ este o singură valoare pentru toată liga, iar într-un meci foarte dezechilibrat ($\lambda_h = 5$, $\rho = -0{,}2$) acea limită ar face un 0–1 imposibil. De aceea niciun $\tau$ nu coboară sub 1/2:

$$-\frac{1}{2\max(\lambda_h, \lambda_a)} \le \rho \le \frac{1}{2}\min\Big(1, \frac{1}{\lambda_h \lambda_a}\Big)$$

și un $\rho$ din afara intervalului este adus la capătul lui. În meciurile obișnuite (ambele $\lambda$ cel mult 2,5), un $\rho$ până la $-0{,}2$ se aplică întreg.

**Ponderile meciurilor recente (Ec. 7, Faza 23).** Cu un timp de înjumătățire $h$ (în meciuri), al $j$-lea cel mai recent meci de acasă (sau din deplasare) al unei echipe, $j = 0$ fiind ultimul, are ponderea

$$w_j = 2^{-j/h}$$

deci un meci jucat cu $h$ meciuri în urmă contează pe jumătate. Fără $h$, toate meciurile au ponderea 1, ca înainte. Ponderile urmează ordinea meciurilor, nu zilele din calendar, așa că pauza de vară nu le scade.

## 4. Intrări

- meciurile anterioare zilei meciului (prin `MatchHistory`, singura regulă de tăiere a proiectului);
- $N$: câte meciuri recente de acasă (respectiv din deplasare) ale fiecărei echipe se folosesc;
- $m$: câte meciuri imaginare de nivel mediu trag forțele spre 1;
- $h$: timpul de înjumătățire al ponderilor (Ec. 7), sau niciunul;
- $\rho$: corecția Dixon–Coles (Ec. 6), 0 fără corecție;
- fereastra ligii: câte meciuri recente se folosesc pentru $\mu_h$ și $\mu_a$;
- $G$: numărul maxim de goluri păstrat în tabel pentru fiecare echipă.

## 5. Ieșiri

- golurile așteptate $\lambda_h$ și $\lambda_a$ și cele patru forțe din care provin;
- tabelul probabilităților tuturor scorurilor până la $G$–$G$ și probabilitatea pierdută prin tăiere;
- probabilitățile $(P(H), P(D), P(A))$, în această ordine, în formatul comun al predicțiilor;
- scorurile cele mai probabile.

## 6. Pseudocod

```
PROBABILITĂȚI_GOLURI(λ, G):                        ▷ Ec. 1
    p[0] ← e^(−λ)
    pentru k ← 1 până la G:
        p[k] ← p[k − 1] · λ / k
    returnează p

PREDICȚIE(meci, istoric, N, m, h, ρ, fereastră_ligă, G):
    D ← data meciului
    μ_h, μ_a ← media golurilor gazdelor și oaspeților în ultimele fereastră_ligă meciuri dinaintea zilei D
    dacă μ_h = 0 sau μ_a = 0: returnează „fără predicție”
    acasă ← ultimele N meciuri de acasă ale gazdelor dinaintea zilei D
    deplasare ← ultimele N meciuri din deplasare ale oaspeților dinaintea zilei D
    w ← 2^(−j / h) pentru al j-lea cel mai recent meci (1 fără h)         ▷ Ec. 7
    FORȚĂ(goluri, n, μ) = ((goluri + m · μ) / (n + m)) / μ               ▷ Ec. 4
    atac_g ← FORȚĂ(Σ w · golurile marcate acasă, Σ w, μ_h)
    apărare_g ← FORȚĂ(Σ w · golurile primite acasă, Σ w, μ_a)
    atac_o ← FORȚĂ(Σ w · golurile marcate în deplasare, Σ w, μ_a)
    apărare_o ← FORȚĂ(Σ w · golurile primite în deplasare, Σ w, μ_h)
    λ_h ← atac_g · apărare_o · μ_h                                      ▷ Ec. 5
    λ_a ← atac_o · apărare_g · μ_a
    p_h ← PROBABILITĂȚI_GOLURI(λ_h, G);  p_a ← PROBABILITĂȚI_GOLURI(λ_a, G)
    T[i, j] ← p_h[i] · p_a[j] pentru 0 ≤ i, j ≤ G                        ▷ Ec. 2
    ρ ← ρ adus în [−1 / (2 max(λ_h, λ_a)), min(1, 1 / (λ_h λ_a)) / 2]
    T[0,0] ← T[0,0] · (1 − λ_h λ_a ρ);  T[0,1] ← T[0,1] · (1 + λ_h ρ)    ▷ Ec. 6
    T[1,0] ← T[1,0] · (1 + λ_a ρ);      T[1,1] ← T[1,1] · (1 − ρ)
    păstrat ← suma lui T;  T ← T / păstrat
    P(H) ← suma lui T[i, j] pentru i > j                                ▷ Ec. 3
    P(D) ← suma lui T[i, i]
    P(A) ← suma lui T[i, j] pentru i < j
    returnează λ_h, λ_a, T, (P(H), P(D), P(A)), 1 − păstrat
```

## 7. Detalii de implementare

### 7.1. Fișiere

| Fișier | Conținut |
|---|---|
| `app/algorithms/poisson.py` | Ec. 1–7: probabilitățile golurilor, tabelul scorurilor (`ScoreDistribution`, cu corecția `low_score_correction` și limita `admissible_rho`), rezultatele, scorurile cele mai probabile, forțele, golurile așteptate și ponderile (`recency_weights`). Folosește doar biblioteca standard Python și NumPy. |
| `app/prediction/poisson_predictions.py` | `predict_match` și `run_poisson`: calculează forțele (din `weighted_record`) și $\lambda$ din meciurile dinaintea zilei fiecărui meci; parametrii aleși sunt valorile implicite. |
| `app/evaluation/poisson_calibration.py` | Alegerea lui $N$, $m$, $h$ și $\rho$: `python -m app.evaluation.poisson_calibration`. |

Tabelul scorurilor nu poate fi modificat după ce este construit. Dacă tăierea la $G$ goluri ar pierde mai mult de 1% din probabilitate, calculul se oprește cu o eroare în loc să dea un rezultat distorsionat. Un meci primește predicție doar după ce liga are cel puțin un gol al gazdelor și unul al oaspeților; pe datele reale, singurul meci fără predicție este cel din prima zi (26 august 2006).

### 7.2. Valorile parametrilor

| Parametru | Valoare | Cum a fost ales |
|---|---|---|
| $N$ | 76 | calibrare (secțiunea 7.3) |
| $m$ | 10 | calibrare (secțiunea 7.3) |
| $h$ | 19 meciuri (un sezon de meciuri acasă) | calibrare (secțiunea 7.3), din Faza 23 |
| $\rho$ | −0,04 | calibrare (secțiunea 7.3), din Faza 23 |
| fereastra ligii | 380 de meciuri | un sezon al unei ligi cu 20 de echipe |
| $G$ | 20 de goluri | vezi mai jos |

Valorile sunt cele ale La Liga. Fiecare ligă are valorile ei, alese pe propriile sezoane de calibrare (rulare din 2026-10-16): Premier League $N = 76$, $m = 5$, $h = 19$, $\rho = -0{,}08$; Serie A $N = 38$, $m = 20$, fără ponderi, $\rho = -0{,}06$; Bundesliga $N = 68$, $m = 10$, $h = 34$, $\rho = -0{,}06$; Ligue 1 $N = 57$, $m = 20$, $h = 19$, $\rho = -0{,}10$. În ligile cu 18 echipe, fereastra ligii are 306 meciuri (`docs/leagues.md`).

**Alegerea lui $G$.** Inițial am ales $G = 10$, cel mai mare număr de goluri din date. Rularea pe datele reale a arătat că alegerea era greșită: ce contează este distribuția modelului, nu scorurile observate. Pentru $\lambda = 4{,}89$ (cea mai mare valoare obținută cu setări de probă, Barcelona – Getafe, martie 2016), tăierea la 10 goluri ar fi pierdut 1,2% din probabilitate:

| $\lambda$ | $G = 10$ | $G = 12$ | $G = 15$ | $G = 20$ |
|---|---|---|---|---|
| 3,50 | 1,0 · 10⁻³ | 7,6 · 10⁻⁵ | 9,2 · 10⁻⁷ | 1,9 · 10⁻¹⁰ |
| 4,89 | 1,2 · 10⁻² | 1,7 · 10⁻³ | 5,3 · 10⁻⁵ | 5,6 · 10⁻⁸ |
| 6,00 | 4,3 · 10⁻² | 8,8 · 10⁻³ | 5,1 · 10⁻⁴ | 1,5 · 10⁻⁶ |

Cu $G = 20$, tabelul are 441 de celule, iar probabilitatea pierdută este neglijabilă. Cu parametrii aleși în Faza 23, cea mai mare valoare $\lambda$ pe toate cele 20 de sezoane ale La Liga este 3,89 (Real Madrid – Granada, 19 septembrie 2015), iar cea mai mare probabilitate pierdută este $1{,}2 \cdot 10^{-9}$ (rulare din 2026-10-16). Limita lui $\rho$ (Ec. 6) nu s-a aplicat la niciun meci al La Liga: cu $\rho = -0{,}04$ ar fi nevoie de un $\lambda$ peste 12,5.

### 7.3. Calibrarea lui N, m, h și ρ

Modelul a fost rulat doar pe sezonul de încălzire 2006/07 și pe sezoanele de calibrare 2007/08–2009/10; sezoanele de evaluare nu sunt citite. Pentru fiecare alegere din grilă ($N \in \{5, 10, 19, 38, 57, 76, 95\}$, adică 5, 10 și unul până la cinci sezoane de meciuri acasă; $m \in \{1, 2, 5, 10, 20, 30, 50, 80\}$; $h$ niciunul sau un sfert, o jumătate, unul, două ori patru sezoane de meciuri acasă, adică 5, 10, 19, 38, 76; $\rho \in \{0; -0{,}02; \ldots; -0{,}2\}$, 3.696 de alegeri) s-a calculat media lui $-\ln P(\text{scorul real})$ pe cele 1.140 de meciuri de calibrare ale La Liga. Măsura a fost aleasă pentru că modelul Poisson prezice întregul tabel al scorurilor, iar probabilitatea dată scorului care s-a produs îl evaluează direct. $\rho$ schimbă doar cele patru scoruri mici și nu schimbă suma tabelului (Ec. 6), așa că modelul rulează o dată pentru fiecare $(N, m, h)$, iar fiecare $\rho$ rescalează doar probabilitatea scorului real când acesta este 0–0, 0–1, 1–0 sau 1–1; un test verifică că rezultatul este același cu al modelului rulat cu acel $\rho$. Rulare din 2026-10-16:

| N | m | h | ρ | Media lui $-\ln P(\text{scorul real})$ |
|---|---|---|---|---|
| **76** | **10** | **19** | **−0,04** | **2,94878** |
| 95 | 10 | 19 | −0,04 | 2,94878 |
| 76 | 10 | 19 | −0,02 | 2,94881 |
| 76 | 10 | 19 | −0,06 | 2,94897 |
| 76 | 10 | 19 | 0 | 2,94906 |
| 76 | 20 | – | 0 | 2,95296 |

Ultimul rând este alegerea de până în Faza 23 (fără ponderi și fără corecție). Ponderile meciurilor recente aduc cea mai mare parte a câștigului (2,95296 → 2,94906), corecția Dixon–Coles foarte puțin (→ 2,94878). Ca referință, același model fără forțele echipelor ($\lambda_h = \mu_h$ și $\lambda_a = \mu_a$ pentru toate meciurile) are 3,02654. Altfel spus, media geometrică a probabilității date scorului real crește de la 4,85% la 5,24%.

La prima rulare din Faza 23 grila lui $h$ se oprea la două sezoane, iar Bundesliga a ales chiar această valoare; grila a fost extinsă cu patru sezoane și Bundesliga a păstrat două sezoane, de data aceasta în interiorul grilei.

Prima grilă se oprea la $m = 20$, iar cea mai bună valoare era chiar la margine. Grila a fost extinsă cu 30, 50 și 80; $m = 20$ a rămas cel mai bun, de data aceasta în interiorul grilei.

Până în Faza 15, grila lui $N$ se oprea la trei sezoane (57), iar valoarea aleasă pentru La Liga era $N = 38$. Când au fost adăugate celelalte ligi, Premier League și Bundesliga și-au ales valoarea maximă a grilei, așa că grila a fost extinsă la cinci sezoane pentru toate ligile. Aceeași regulă dă acum La Liga $N = 76$, cu o îmbunătățire foarte mică (2,95296 față de 2,95326). $N = 76$ și $N = 95$ dau exact același rezultat: în sezoanele de calibrare nicio echipă nu avea mai mult de 75 de meciuri acasă anterioare, deci ambele ferestre folosesc tot istoricul disponibil. Calibrarea nu poate deosebi ferestrele mai lungi de patru sezoane; la egalitate este aleasă valoarea mai mică.

### 7.4. Diagnostic pe sezoanele de calibrare

Cu $N = 76$, $m = 10$, $h = 19$ și $\rho = -0{,}04$, pe cele 1.140 de meciuri ale La Liga din 2007/08–2009/10 (rulare din 2026-10-16):

| Mărime | Prezis | Real |
|---|---|---|
| Goluri gazde pe meci (media lui $\lambda_h$) | 1,523 | 1,604 |
| Goluri oaspeți pe meci (media lui $\lambda_a$) | 1,156 | 1,162 |
| Victorii gazde | 45,0% | 49,1% |
| Egaluri | 25,8% | 23,2% |
| Victorii oaspeți | 29,1% | 27,6% |
| Scor 0–0 | 7,8% | 6,7% |
| Scor 1–1 | 12,1% | 11,8% |
| Scor 1–0 | 10,0% | 10,9% |
| Scor 2–1 | 8,6% | 8,5% |

- Eroarea absolută medie a golurilor așteptate este 0,9282 goluri (0,9264 înainte de Faza 23), față de 0,9823 când se folosesc doar mediile ligii.
- Scorul cel mai probabil a fost scorul real în 11,7% dintre meciuri.
- Literatura de specialitate arată că modelul Poisson cu goluri independente subestimează de obicei egalurile. Pe sezoanele noastre de calibrare ale La Liga nu s-a întâmplat acest lucru: modelul a prezis mai multe egaluri decât au fost (25,8% față de 23,2%). De aceea corecția aleasă pentru La Liga este mică ($\rho = -0{,}04$); celelalte ligi au ales între −0,06 și −0,10.
- Modelul a subestimat golurile gazdelor (1,523 față de 1,604) și, de aceea, victoriile gazdelor. Media ligii este calculată din ultimele 380 de meciuri, deci reacționează cu întârziere. Golurile gazdelor au crescut de la 1,36 pe meci în 2006/07 la 1,55–1,66 în sezoanele de calibrare.

### 7.5. Modificări în Faza 23: meciurile recente și corecția Dixon–Coles

Echipa a cerut ca meciurile recente să conteze mai mult și ca egalurile să fie corectate. Ec. 6 și Ec. 7 au fost adăugate ca opțiuni ale grilei de calibrare: fiecare ligă a ales o corecție ($\rho$ între −0,04 și −0,10), iar toate ligile în afară de Serie A au ales ponderi (un sezon de meciuri acasă; Bundesliga două). Pe sezoanele de evaluare (2010/11–2025/26), comparat meci cu meci cu modelul de dinainte, scorul Brier s-a schimbat cu −0,0043 (Premier League), −0,0008 (La Liga), −0,0003 (Serie A), −0,0030 (Bundesliga) și −0,0011 (Ligue 1); diferențele din Premier League și Bundesliga sunt reale. Pe toate cele cinci ligi la un loc, −0,0019, cu intervalul [−0,0025; −0,0013]: o îmbunătățire reală, dar mică. Poisson rămâne totuși modelul cel mai slab dintre cele trei (`docs/leagues.md`).

## 8. Complexitate

Notații: $G$ — numărul maxim de goluri; $n$ — numărul de meciuri; $N$ — fereastra echipelor; $L$ — fereastra ligii; $g$ — numărul de perechi din grila de calibrare; $n_c$ — numărul de meciuri din sezoanele de încălzire și calibrare.

| Operație | Timp | Memorie |
|---|---|---|
| Probabilitățile golurilor unei echipe (Ec. 1) | O(G) | O(G) |
| Tabelul scorurilor și cele trei rezultate (Ec. 2–3) | O(G²) | O(G²) |
| Scorurile cele mai probabile | O(G² log G) | O(G²) |
| Ponderile ultimelor $N$ meciuri (Ec. 7) | O(N) | O(N) |
| Corecția scorurilor mici (Ec. 6) | O(1) | O(1) |
| Forțele și $\lambda$ pentru un meci (Ec. 4–5, 7) | O(log n + N + L) | O(N + L) |
| Rularea pe tot istoricul (`run_poisson`) | O(n (log n + N + L + G²)) | O(n G²) pentru predicțiile salvate |
| Calibrarea | O(g · n_c (log n_c + N + L + G²) + g · r · n_c) | O(n_c G²) |

Aici $g$ este numărul de alegeri $(N, m, h)$, iar $r$ numărul de valori $\rho$: fiecare $\rho$ costă doar O(1) pe meci, fără o nouă rulare. Selecția meciurilor anterioare folosește căutarea binară din `MatchHistory` (secțiunea 6 din `docs/architecture.md`). Pe datele reale ale La Liga, toate cele 7.599 de predicții se calculează în aproximativ 0,7 s, iar calibrarea pe cele 3.696 de alegeri (cu pornirea programului și citirea bazei de date) în aproximativ 36 s (rulare din 2026-10-16).

## 9. Ipoteze

- Numărul de goluri al fiecărei echipe urmează o distribuție Poisson.
- Golurile gazdelor și ale oaspeților sunt independente, în afară de cele patru scoruri mici corectate prin Ec. 6.
- Forța unei echipe acasă și în deplasare se poate descrie prin raportul dintre golurile ei și media ligii, iar efectele atacului și apărării se înmulțesc (Ec. 5).
- Ultimele $N$ meciuri, cele recente cântărind mai mult (Ec. 7), descriu suficient de bine forța actuală a unei echipe.

## 10. Limitări

- Ipoteza independenței ignoră legătura dintre golurile celor două echipe (de exemplu, o echipă condusă care atacă mai mult). Corecția Dixon–Coles (Ec. 6) tratează doar cele patru scoruri mici, cu un singur $\rho$ pe ligă ales pe sezoanele de calibrare, nu estimat împreună cu forțele prin verosimilitate maximă, ca la Dixon și Coles.
- O echipă nou promovată pornește ca o echipă medie (forța 1), deși de obicei este mai slabă. O echipă care revine după câțiva ani poate fi descrisă de meciuri vechi, pentru că fereastra de $N$ meciuri și ponderile urmează ordinea meciurilor, nu timpul.
- Media ligii reacționează cu întârziere la schimbări (vezi secțiunea 7.4).
- Nu ține cont de forma recentă, de accidentări, de transferuri sau de puterea adversarilor întâlniți anterior: 3 goluri marcate unei echipe slabe contează la fel ca 3 goluri marcate unei echipe puternice.
- Calibrarea folosește doar trei sezoane (1.140 de meciuri) și nu poate deosebi ferestrele $N$ mai lungi decât istoricul disponibil atunci (secțiunea 7.3).

## 11. Exemple din teste

Testele sunt în `tests/test_poisson.py`, `tests/test_poisson_predictions.py` și `tests/test_poisson_calibration.py`.

- Pentru $\lambda = 1$: $P(0) = P(1) = e^{-1} = 0{,}3679$ și $P(2) = e^{-1}/2$; $P(3; 2{,}5) = 0{,}2138$.
- Recurența coincide cu formula cu factoriale până la 12 cifre; probabilitățile au suma 1, iar media golurilor este $\lambda$, chiar și pentru $\lambda = 50$.
- Dacă oaspeții nu marchează niciodată ($\lambda_a = 0$) și $\lambda_h = 1$: $(P(H), P(D), P(A)) = (1 - e^{-1}, e^{-1}, 0)$.
- Valori $\lambda$ egale dau șanse egale de victorie; inversarea echipelor transpune tabelul.
- Pentru $\lambda_h = 1{,}6$ și $\lambda_a = 0{,}9$, scorurile cele mai probabile sunt 1–0 (13,1%), 1–1 și 2–0.
- Exemplu calculat de mână: cu mediile ligii 1,5 și 1,0 și forțele 1,1667 / 1,0 / 1,5 / 0,5, rezultă $\lambda_h = 0{,}875$ și $\lambda_a = 1{,}5$.
- Calibrarea: după un 1–1, ambele valori $\lambda$ sunt 1, iar pierderea pentru un 1–0 este exact $-\ln(e^{-2}) = 2$; cu $\rho = -0{,}1$, $\tau(1,0) = 0{,}9$ și pierderea devine $2 - \ln 0{,}9$.
- Corecția Dixon–Coles: pentru $\lambda_h = 1$, $\lambda_a = 2$, $\rho = -0{,}1$, $\tau$ este (1,2; 0,9 / 0,8; 1,1); pentru $\lambda_h = \lambda_a = 1$ și $\rho = -0{,}1$, egalul câștigă exact $0{,}2\,e^{-2}$, iar fiecare victorie pierde $0{,}1\,e^{-2}$; suma tabelului și golurile așteptate rămân aceleași; pentru $\lambda_h = 5$, $\rho = -0{,}2$ este limitat la $-0{,}1$, iar 0–1 își păstrează jumătate din probabilitate.
- Ponderile: cu $h = 1$, trei meciuri au ponderile 0,25, 0,5 și 1; într-un exemplu calculat de mână, un 2–1 vechi (ponderea 0,5) și un 0–0 recent (ponderea 1) dau 1 gol marcat în 1,5 meciuri ponderate.
- Fără scurgere de informații: schimbarea rezultatului unui meci nu modifică nicio predicție din ziua lui sau dinainte, dar modifică predicțiile ulterioare.

## 12. Rolul în PitchSense

- Este al doilea algoritm de predicție. Pentru fiecare meci oferă probabilitățile victorie gazde / egal / victorie oaspeți, comparabile direct cu cele ale ratingului Elo și ale regresiei logistice (fazele 8–10).
- Este singurul algoritm care prezice scorul: ecranul Predicție afișează golurile așteptate, scorurile cele mai probabile și graficul probabilităților scorurilor de la 0-0 la 6-6 (Faza 12).
- Golurile așteptate permit metrica „eroarea absolută medie a golurilor așteptate” din evaluare.

Exemplu pentru un meci din sezonul 2025/26 (Real Madrid – Barcelona, 26 octombrie 2025), calculat doar din meciurile anterioare, cu setările din Faza 23: $\lambda_h = 1{,}74$, $\lambda_a = 1{,}45$; probabilități 44,2% / 24,0% / 31,8%; scorurile cele mai probabile 1–1 (10,8%), 2–1 (9,0%) și 1–2 (7,5%). Scorul real a fost 2–1. Exemplul ilustrează forma predicției; evaluarea modelului se face în fazele 8–10.

## 13. Surse

- Maher, M. J. (1982). Modelling association football scores. *Statistica Neerlandica*, 36(3), 109–118.
- Dixon, M. J., & Coles, S. G. (1997). Modelling association football scores and inefficiencies in the football betting market. *Journal of the Royal Statistical Society: Series C (Applied Statistics)*, 46(2), 265–280.

Maher a propus descrierea golurilor fiecărei echipe prin distribuții Poisson cu parametri de atac și de apărare; Dixon și Coles au propus corecția $\tau$ a scorurilor mici și ponderi care scad cu vechimea meciurilor. Noi folosim o variantă simplificată: forțe calculate direct din medii ponderate (Ec. 4–5, 7), nu estimate prin verosimilitate maximă; ponderile scad cu numărul de meciuri, nu cu timpul; $\rho$ este ales pe sezoanele de calibrare, nu estimat; iar $\tau$ nu coboară sub 1/2. Codul a fost scris pornind de la formulele de mai sus, nu copiat dintr-o implementare existentă.

## 14. Reproducere

```bash
python -m app.data.build_database
python -m app.evaluation.poisson_calibration SP1
python -m app.evaluation.league_calibration
```
