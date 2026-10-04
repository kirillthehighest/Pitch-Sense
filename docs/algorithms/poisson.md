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

Pentru atac se folosesc golurile marcate, iar pentru apărare golurile primite: o valoare peste 1 înseamnă o apărare mai slabă decât media. Fără niciun meci anterior, forța este exact 1.

**Golurile așteptate (Ec. 5).** Cu $\mu_h$ și $\mu_a$ media golurilor gazdelor și oaspeților în ligă:

$$\lambda_h = \text{atac}_{\text{gazde, acasă}} \cdot \text{apărare}_{\text{oaspeți, deplasare}} \cdot \mu_h, \qquad \lambda_a = \text{atac}_{\text{oaspeți, deplasare}} \cdot \text{apărare}_{\text{gazde, acasă}} \cdot \mu_a$$

Forța gazdelor se calculează doar din meciurile lor de acasă, iar cea a oaspeților doar din meciurile lor din deplasare.

## 4. Intrări

- meciurile anterioare zilei meciului (prin `MatchHistory`, singura regulă de tăiere a proiectului);
- $N$: câte meciuri recente de acasă (respectiv din deplasare) ale fiecărei echipe se folosesc;
- $m$: câte meciuri imaginare de nivel mediu trag forțele spre 1;
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

PREDICȚIE(meci, istoric, N, m, fereastră_ligă, G):
    D ← data meciului
    μ_h, μ_a ← media golurilor gazdelor și oaspeților în ultimele fereastră_ligă meciuri dinaintea zilei D
    dacă μ_h = 0 sau μ_a = 0: returnează „fără predicție”
    acasă ← ultimele N meciuri de acasă ale gazdelor dinaintea zilei D
    deplasare ← ultimele N meciuri din deplasare ale oaspeților dinaintea zilei D
    FORȚĂ(goluri, n, μ) = ((goluri + m · μ) / (n + m)) / μ               ▷ Ec. 4
    atac_g ← FORȚĂ(golurile marcate acasă, |acasă|, μ_h)
    apărare_g ← FORȚĂ(golurile primite acasă, |acasă|, μ_a)
    atac_o ← FORȚĂ(golurile marcate în deplasare, |deplasare|, μ_a)
    apărare_o ← FORȚĂ(golurile primite în deplasare, |deplasare|, μ_h)
    λ_h ← atac_g · apărare_o · μ_h                                      ▷ Ec. 5
    λ_a ← atac_o · apărare_g · μ_a
    p_h ← PROBABILITĂȚI_GOLURI(λ_h, G);  p_a ← PROBABILITĂȚI_GOLURI(λ_a, G)
    T[i, j] ← p_h[i] · p_a[j] pentru 0 ≤ i, j ≤ G                        ▷ Ec. 2
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
| `app/algorithms/poisson.py` | Ec. 1–5: probabilitățile golurilor, tabelul scorurilor (`ScoreDistribution`), rezultatele, scorurile cele mai probabile, forțele și golurile așteptate. Folosește doar biblioteca standard Python și NumPy. |
| `app/prediction/poisson_predictions.py` | `predict_match` și `run_poisson`: calculează forțele și $\lambda$ din statisticile dinaintea zilei fiecărui meci; parametrii aleși sunt valorile implicite. |
| `app/evaluation/poisson_calibration.py` | Alegerea lui $N$ și $m$: `python -m app.evaluation.poisson_calibration`. |

Tabelul scorurilor nu poate fi modificat după ce este construit. Dacă tăierea la $G$ goluri ar pierde mai mult de 1% din probabilitate, calculul se oprește cu o eroare în loc să dea un rezultat distorsionat. Un meci primește predicție doar după ce liga are cel puțin un gol al gazdelor și unul al oaspeților; pe datele reale, singurul meci fără predicție este cel din prima zi (26 august 2006).

### 7.2. Valorile parametrilor

| Parametru | Valoare | Cum a fost ales |
|---|---|---|
| $N$ | 38 | calibrare (secțiunea 7.3) |
| $m$ | 20 | calibrare (secțiunea 7.3) |
| fereastra ligii | 380 de meciuri | un sezon al unei ligi cu 20 de echipe |
| $G$ | 20 de goluri | vezi mai jos |

**Alegerea lui $G$.** Inițial am ales $G = 10$, cel mai mare număr de goluri din date. Rularea pe datele reale a arătat că alegerea era greșită: ce contează este distribuția modelului, nu scorurile observate. Pentru $\lambda = 4{,}89$ (cea mai mare valoare obținută cu setări de probă, Barcelona – Getafe, martie 2016), tăierea la 10 goluri ar fi pierdut 1,2% din probabilitate:

| $\lambda$ | $G = 10$ | $G = 12$ | $G = 15$ | $G = 20$ |
|---|---|---|---|---|
| 3,50 | 1,0 · 10⁻³ | 7,6 · 10⁻⁵ | 9,2 · 10⁻⁷ | 1,9 · 10⁻¹⁰ |
| 4,89 | 1,2 · 10⁻² | 1,7 · 10⁻³ | 5,3 · 10⁻⁵ | 5,6 · 10⁻⁸ |
| 6,00 | 4,3 · 10⁻² | 8,8 · 10⁻³ | 5,1 · 10⁻⁴ | 1,5 · 10⁻⁶ |

Cu $G = 20$, tabelul are 441 de celule, iar probabilitatea pierdută este neglijabilă. Cu parametrii aleși, cea mai mare valoare $\lambda$ pe toate cele 20 de sezoane este 3,65, iar cea mai mare probabilitate pierdută este $3{,}9 \cdot 10^{-10}$.

### 7.3. Calibrarea lui N și m

Modelul a fost rulat doar pe sezonul de încălzire 2006/07 și pe sezoanele de calibrare 2007/08–2009/10; sezoanele de evaluare nu sunt citite. Pentru fiecare pereche din grilă ($N \in \{5, 10, 19, 38, 57\}$, $m \in \{1, 2, 5, 10, 20, 30, 50, 80\}$) s-a calculat media lui $-\ln P(\text{scorul real})$ pe cele 1.140 de meciuri de calibrare. Măsura a fost aleasă pentru că modelul Poisson prezice întregul tabel al scorurilor, iar probabilitatea dată scorului care s-a produs îl evaluează direct. Rulare din 2026-10-04:

| N | m | Media lui $-\ln P(\text{scorul real})$ |
|---|---|---|
| **38** | **20** | **2,95326** |
| 57 | 20 | 2,95390 |
| 38 | 10 | 2,95551 |
| 57 | 30 | 2,95587 |
| 38 | 30 | 2,95623 |

Ca referință, același model fără forțele echipelor ($\lambda_h = \mu_h$ și $\lambda_a = \mu_a$ pentru toate meciurile) are 3,02654. Altfel spus, media geometrică a probabilității date scorului real crește de la 4,85% la 5,22%.

Prima grilă se oprea la $m = 20$, iar cea mai bună valoare era chiar la margine. Grila a fost extinsă cu 30, 50 și 80; $m = 20$ a rămas cel mai bun, de data aceasta în interiorul grilei, la fel ca $N = 38$.

### 7.4. Diagnostic pe sezoanele de calibrare

Cu $N = 38$ și $m = 20$, pe cele 1.140 de meciuri din 2007/08–2009/10:

| Mărime | Prezis | Real |
|---|---|---|
| Goluri gazde pe meci (media lui $\lambda_h$) | 1,522 | 1,604 |
| Goluri oaspeți pe meci (media lui $\lambda_a$) | 1,157 | 1,162 |
| Victorii gazde | 45,5% | 49,1% |
| Egaluri | 25,0% | 23,2% |
| Victorii oaspeți | 29,5% | 27,6% |
| Scor 0–0 | 7,3% | 6,7% |
| Scor 1–1 | 11,7% | 11,8% |
| Scor 1–0 | 10,5% | 10,9% |
| Scor 2–1 | 8,7% | 8,5% |

- Eroarea absolută medie a golurilor așteptate este 0,9314 goluri, față de 0,9823 când se folosesc doar mediile ligii.
- Scorul cel mai probabil a fost scorul real în 11,1% dintre meciuri.
- Literatura de specialitate arată că modelul Poisson cu goluri independente subestimează de obicei egalurile. Pe sezoanele noastre de calibrare nu s-a întâmplat acest lucru: modelul a prezis puțin mai multe egaluri decât au fost (25,0% față de 23,2%).
- Modelul a subestimat golurile gazdelor (1,522 față de 1,604) și, de aceea, victoriile gazdelor. Media ligii este calculată din ultimele 380 de meciuri, deci reacționează cu întârziere. Golurile gazdelor au crescut de la 1,36 pe meci în 2006/07 la 1,55–1,66 în sezoanele de calibrare.

## 8. Complexitate

Notații: $G$ — numărul maxim de goluri; $n$ — numărul de meciuri; $N$ — fereastra echipelor; $L$ — fereastra ligii; $g$ — numărul de perechi din grila de calibrare; $n_c$ — numărul de meciuri din sezoanele de încălzire și calibrare.

| Operație | Timp | Memorie |
|---|---|---|
| Probabilitățile golurilor unei echipe (Ec. 1) | O(G) | O(G) |
| Tabelul scorurilor și cele trei rezultate (Ec. 2–3) | O(G²) | O(G²) |
| Scorurile cele mai probabile | O(G² log G) | O(G²) |
| Forțele și $\lambda$ pentru un meci (Ec. 4–5) | O(log n + N + L) | O(N + L) |
| Rularea pe tot istoricul (`run_poisson`) | O(n (log n + N + L + G²)) | O(n G²) pentru predicțiile salvate |
| Calibrarea | O(g · n_c (log n_c + N + L + G²)) | O(n_c G²) |

Selecția meciurilor anterioare folosește căutarea binară din `MatchHistory` (secțiunea 6 din `docs/architecture.md`). Pe datele reale, toate cele 7.599 de predicții se calculează în aproximativ 0,6 s, iar calibrarea pe 40 de perechi (cu pornirea programului și citirea bazei de date) în aproximativ 4,5 s.

## 9. Ipoteze

- Numărul de goluri al fiecărei echipe urmează o distribuție Poisson.
- Golurile gazdelor și ale oaspeților sunt independente.
- Forța unei echipe acasă și în deplasare se poate descrie prin raportul dintre golurile ei și media ligii, iar efectele atacului și apărării se înmulțesc (Ec. 5).
- Ultimele $N$ meciuri descriu suficient de bine forța actuală a unei echipe.

## 10. Limitări

- Ipoteza independenței ignoră legătura dintre golurile celor două echipe (de exemplu, o echipă condusă care atacă mai mult). Corecția Dixon–Coles ar trata acest lucru, dar nu face parte din proiect.
- O echipă nou promovată pornește ca o echipă medie (forța 1), deși de obicei este mai slabă. O echipă care revine după câțiva ani poate fi descrisă de meciuri vechi, pentru că fereastra de $N$ meciuri nu ține cont de timp.
- Media ligii reacționează cu întârziere la schimbări (vezi secțiunea 7.4).
- Nu ține cont de forma recentă, de accidentări, de transferuri sau de puterea adversarilor întâlniți anterior: 3 goluri marcate unei echipe slabe contează la fel ca 3 goluri marcate unei echipe puternice.
- Calibrarea folosește doar trei sezoane (1.140 de meciuri).

## 11. Exemple din teste

Testele sunt în `tests/test_poisson.py`, `tests/test_poisson_predictions.py` și `tests/test_poisson_calibration.py`.

- Pentru $\lambda = 1$: $P(0) = P(1) = e^{-1} = 0{,}3679$ și $P(2) = e^{-1}/2$; $P(3; 2{,}5) = 0{,}2138$.
- Recurența coincide cu formula cu factoriale până la 12 cifre; probabilitățile au suma 1, iar media golurilor este $\lambda$, chiar și pentru $\lambda = 50$.
- Dacă oaspeții nu marchează niciodată ($\lambda_a = 0$) și $\lambda_h = 1$: $(P(H), P(D), P(A)) = (1 - e^{-1}, e^{-1}, 0)$.
- Valori $\lambda$ egale dau șanse egale de victorie; inversarea echipelor transpune tabelul.
- Pentru $\lambda_h = 1{,}6$ și $\lambda_a = 0{,}9$, scorurile cele mai probabile sunt 1–0 (13,1%), 1–1 și 2–0.
- Exemplu calculat de mână: cu mediile ligii 1,5 și 1,0 și forțele 1,1667 / 1,0 / 1,5 / 0,5, rezultă $\lambda_h = 0{,}875$ și $\lambda_a = 1{,}5$.
- Calibrarea: după un 1–1, ambele valori $\lambda$ sunt 1, iar pierderea pentru un 1–0 este exact $-\ln(e^{-2}) = 2$.
- Fără scurgere de informații: schimbarea rezultatului unui meci nu modifică nicio predicție din ziua lui sau dinainte, dar modifică predicțiile ulterioare.

## 12. Rolul în PitchSense

- Este al doilea algoritm de predicție. Pentru fiecare meci oferă probabilitățile victorie gazde / egal / victorie oaspeți, comparabile direct cu cele ale ratingului Elo și ale regresiei logistice (fazele 8–10).
- Este singurul algoritm care prezice scorul: fila Match Prediction afișează golurile așteptate, scorurile cele mai probabile și graficul probabilităților scorurilor de la 0-0 la 6-6 (Faza 12).
- Golurile așteptate permit metrica „eroarea absolută medie a golurilor așteptate” din evaluare.

Exemplu pentru un meci din sezonul 2025/26 (Real Madrid – Barcelona, 26 octombrie 2025), calculat doar din meciurile anterioare: $\lambda_h = 1{,}75$, $\lambda_a = 1{,}43$; probabilități 45,1% / 23,2% / 31,7%; scorurile cele mai probabile 1–1 (10,4%), 2–1 (9,1%) și 1–2 (7,5%). Scorul real a fost 2–1. Exemplul ilustrează forma predicției; evaluarea modelului se face în fazele 8–10.

## 13. Surse

- Maher, M. J. (1982). Modelling association football scores. *Statistica Neerlandica*, 36(3), 109–118.
- Dixon, M. J., & Coles, S. G. (1997). Modelling association football scores and inefficiencies in the football betting market. *Journal of the Royal Statistical Society: Series C (Applied Statistics)*, 46(2), 265–280.

Maher a propus descrierea golurilor fiecărei echipe prin distribuții Poisson cu parametri de atac și de apărare; Dixon și Coles au discutat limitele ipotezei de independență. Noi folosim o variantă simplificată, cu forțe calculate direct din medii (Ec. 4–5), nu estimate prin verosimilitate maximă. Codul a fost scris pornind de la formulele de mai sus, nu copiat dintr-o implementare existentă.

## 14. Reproducere

```bash
python -m app.data.build_database
python -m app.evaluation.poisson_calibration
```
