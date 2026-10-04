# K-Means

Acest document descrie implementarea noastră a algoritmului K-Means din `app/algorithms/kmeans.py` și felul în care este folosit în PitchSense. Algoritmul este scris de la zero cu NumPy, fără biblioteci de învățare automată. Ecuațiile sunt numerotate la fel ca în cod.

## 1. Problema rezolvată

K-Means împarte un set de puncte în $k$ grupuri (clustere), astfel încât punctele dintr-un grup să fie cât mai apropiate de centrul grupului lor. În PitchSense, un punct este profilul unei echipe într-un sezon, adică șase indicatori pe meci. Grupurile obținute descriu tipurile de echipe din La Liga, de exemplu „elita” sau „echipe slabe peste tot”.

## 2. Rolul analitic (de ce este folosit)

K-Means nu prezice rezultatul meciurilor și nu este evaluat prin acuratețe. Are două roluri:

1. **Profilurile echipelor (descriptiv).** Toate cele 400 de profiluri echipă-sezon (20 de sezoane × 20 de echipe) sunt grupate, iar interfața (analiza unei echipe) va arăta tipul fiecărei echipe. Aceste grupuri folosesc sezoane întregi, sunt marcate ca descriptive și nu sunt niciodată intrări pentru predicții. Corespund obiectivului din propunerea de proiect: „identificarea unor tipare comune de performanță”.
2. **Unde funcționează fiecare metodă (pentru evaluare).** În Faza 10, rezultatele ratingului Elo, ale modelului Poisson și ale regresiei logistice vor fi analizate pe tipuri de meciuri, de exemplu „elită contra echipă slabă”. Grupul unei echipe pentru sezonul S se obține fără scurgere de informații: centrele sunt calculate doar din sezoanele dinaintea lui S, iar echipa este plasată după profilul ei din sezonul S − 1. Echipele promovate nu au un sezon anterior în La Liga și formează un grup separat, „promovate”.

## 3. De ce este potrivit

- Profilurile sunt vectori numerici de aceeași lungime, iar distanța euclidiană între profiluri standardizate măsoară cât de diferite sunt două echipe.
- Rezultatul se interpretează ușor: fiecare grup are un centru, adică profilul mediu al echipelor din el.
- Este rapid: o iterație costă O(n k d).
- Numărul de grupuri $k$ se poate alege pe baza unor măsuri explicite (inerție, silhouette, stabilitate).

## 4. Principiul matematic

Notații: $n$ — numărul de puncte, $d$ — numărul de caracteristici, $k$ — numărul de grupuri, $x_i$ — punctul $i$ (standardizat), $\mu_j$ — centrul grupului $j$.

**Standardizarea.** Fiecare caracteristică este transformată în $(x - \text{medie}) / \text{abatere standard}$, ca să conteze la fel, indiferent de unitatea ei de măsură.

**Distanța (Ec. 1):** $D(x, \mu) = \lVert x - \mu \rVert^2$, pătratul distanței euclidiene.

**Atribuirea (Ec. 2):** fiecare punct trece în grupul celui mai apropiat centru:

$$c_i = \arg\min_j D(x_i, \mu_j)$$

**Actualizarea (Ec. 3):** fiecare centru devine media punctelor din grupul lui:

$$\mu_j = \frac{1}{|\{i : c_i = j\}|} \sum_{i : c_i = j} x_i$$

**Inerția (Ec. 4):** $J = \sum_i D(x_i, \mu_{c_i})$. Atribuirea și actualizarea nu cresc niciodată $J$, deci algoritmul se oprește după un număr finit de pași.

**Centrele inițiale k-means++ (Ec. 5).** Primul centru este un punct ales aleator. Fiecare centru următor este un punct ales cu probabilitatea proporțională cu $D(x)^2$, pătratul distanței până la cel mai apropiat centru deja ales. Astfel, centrele inițiale sunt răspândite, iar un punct deja ales nu poate fi ales din nou.

**Oprirea (Ec. 6):** când niciun punct nu își schimbă grupul sau după 300 de iterații.

**Grup gol (Ec. 7):** dacă un grup rămâne fără puncte, centrul lui se mută în punctul cel mai îndepărtat de propriul centru. Dacă sunt mai multe grupuri goale, fiecare primește următorul punct cel mai îndepărtat.

**Silhouette (Ec. 8):** pentru punctul $i$, $a_i$ este distanța medie până la celelalte puncte din grupul lui, iar $b_i$ este distanța medie până la punctele celui mai apropiat alt grup:

$$s(i) = \frac{b_i - a_i}{\max(a_i, b_i)}$$

cu $s(i) = 0$ pentru un punct singur în grupul lui. Media lui $s(i)$ este între −1 și 1; o valoare mare înseamnă grupuri bine separate.

**Indicele Rand (stabilitate):** fracțiunea perechilor de puncte pentru care două grupări sunt de acord (ambele le pun împreună sau ambele le despart). Valoarea 1 înseamnă grupări identice, indiferent de numerele grupurilor.

**Mai multe porniri.** Algoritmul rulează de 10 ori, din centre k-means++ diferite, iar rularea cu cea mai mică inerție este păstrată. Toate alegerile aleatoare vin dintr-un generator cu sămânță fixă, deci rezultatele se repetă.

**Numerotarea grupurilor.** Numerele clusterelor sunt arbitrare și se schimbă de la o rulare la alta. De aceea grupurile sunt raportate după rangul centrului lor după puncte pe meci: grupul 0 este cel mai puternic.

## 5. Intrări

Profilul unei echipe într-un sezon complet (`app/statistics/team_profiles.py`), cu valori pe meci:

| Caracteristică | Semnificație |
|---|---|
| goluri marcate | atacul |
| goluri primite | apărarea |
| șuturi pe poartă | crearea de ocazii |
| șuturi pe poartă primite | ocaziile permise |
| puncte | rezultatele |
| puncte acasă minus puncte în deplasare | cât depinde echipa de terenul propriu |

Alte intrări: $k$, numărul de porniri, sămânța generatorului, numărul maxim de iterații.

## 6. Ieșiri

- centrele grupurilor (și în unitățile originale) și grupul fiecărui profil;
- inerția și istoricul ei pe iterații, dacă algoritmul a convers;
- media silhouette și stabilitatea între porniri diferite (pentru alegerea lui $k$);
- grupurile momentane ale echipelor unui sezon (0 = cel mai puternic; „promovată” = fără grup).

## 7. Pseudocod

```
K_MEANS(X, k, porniri, sămânță):
    standardizează fiecare coloană a lui X
    cea_mai_bună ← nimic
    repetă de „porniri” ori:
        μ ← K_MEANS_PLUS_PLUS(X, k)                                 ▷ Ec. 5
        c ← cel mai apropiat centru pentru fiecare punct            ▷ Ec. 2
        repetă de cel mult 300 de ori:
            pentru fiecare grup j:
                dacă j are puncte: μ_j ← media punctelor lui         ▷ Ec. 3
            pentru fiecare grup j fără puncte:
                μ_j ← punctul cel mai îndepărtat de propriul centru  ▷ Ec. 7
            c_nou ← cel mai apropiat centru pentru fiecare punct
            dacă c_nou = c: oprește                                 ▷ Ec. 6
            c ← c_nou
        J ← suma distanțelor până la centrele proprii              ▷ Ec. 4
        dacă J < J(cea_mai_bună): cea_mai_bună ← (μ, c, J)
    returnează cea_mai_bună

K_MEANS_PLUS_PLUS(X, k):
    μ_1 ← un punct ales uniform aleator
    pentru j ← 2 până la k:
        D(x) ← distanța pătrată de la x la cel mai apropiat centru ales
        μ_j ← un punct ales cu probabilitatea D(x) / Σ D
    returnează μ

GRUPURI_MOMENTANE(sezonul S, k):
    centre ← K_MEANS(profilurile tuturor sezoanelor dinaintea lui S, k)
    pentru fiecare echipă e din S:
        dacă e are profil în sezonul S − 1:
            grup(e) ← rangul celui mai apropiat centru după puncte pe meci
        altfel:
            grup(e) ← „promovată”
```

## 8. Detalii de implementare

### 8.1. Fișiere

| Fișier | Conținut |
|---|---|
| `app/algorithms/kmeans.py` | Ec. 1–8: standardizarea, distanțele, atribuirea, actualizarea, grupurile goale, k-means++, rulările multiple, silhouette. Folosește doar NumPy. |
| `app/statistics/team_profiles.py` | Profilurile echipă-sezon, prin `MatchHistory`. |
| `app/evaluation/team_clustering.py` | Grupurile descriptive, grupurile momentane și ordonarea grupurilor după puncte; `CLUSTER_COUNT = 4`. |
| `app/evaluation/kmeans_selection.py` | Compararea valorilor lui $k$ și descrierea grupurilor: `python -m app.evaluation.kmeans_selection`. |

Algoritmul refuză un $k$ mai mare decât numărul de puncte distincte, pentru că atunci unele grupuri nu ar putea avea niciun punct. Modulul K-Means are propria standardizare (nu o împrumută de la regresia logistică), pentru ca cei patru algoritmi să rămână complet independenți.

### 8.2. Valorile parametrilor

| Parametru | Valoare | Cum a fost ales |
|---|---|---|
| $k$ | 4 | ales de echipă pe baza comparației din secțiunea 8.3 |
| porniri | 10 | valoare implicită documentată |
| sămânța generatorului | 0 | valoare implicită documentată |
| număr maxim de iterații | 300 | valoare implicită; rularea aleasă se oprește după 37 |

### 8.3. Alegerea lui k

$k$ a fost ales doar pe profilurile sezoanelor de încălzire și calibrare (2006/07–2009/10, 80 de profiluri), pentru că hiperparametrii nu se aleg pe perioada raportată. Rulare din 2026-10-04:

| k | Inerția | Scăderea | Silhouette | Stabilitatea (Rand) | Cel mai mic grup |
|---|---|---|---|---|---|
| 2 | 304,3 | – | 0,337 | 1,000 | 25 |
| 3 | 246,1 | 19,1% | 0,277 | 0,974 | 15 |
| **4** | **193,3** | **21,5%** | **0,293** | **1,000** | **3** |
| 5 | 167,5 | 13,3% | 0,239 | 0,972 | 4 |
| 6 | 151,4 | 9,6% | 0,216 | 0,919 | 3 |
| 7 | 138,8 | 8,3% | 0,220 | 0,889 | 3 |
| 8 | 121,8 | 12,3% | 0,239 | 0,910 | 3 |

- $k = 2$ are cea mai mare valoare silhouette, dar separă doar echipele bune de restul, ceea ce este prea grosier pentru analiză.
- $k = 4$ are cea mai mare scădere a inerției, a doua valoare silhouette și stabilitate perfectă între cele 10 porniri. De aceea a fost ales.
- Valorile silhouette sunt mici pentru orice $k$ (0,22–0,40; pentru trei grupuri simulate bine separate valoarea este 0,90). Profilurile echipelor formează mai degrabă un continuu decât grupuri clar separate, deci grupurile descriu tipuri de-a lungul unui spectru.

Ca referință (fără să fi fost folosit la alegere), pe toate cele 400 de profiluri $k = 4$ are scăderea 15,0%, silhouette 0,226 și stabilitatea 0,832: cele două grupuri din jumătatea de jos a clasamentului se suprapun parțial.

### 8.4. Grupurile pe toate sezoanele

Cu $k = 4$, pe toate cele 400 de profiluri (descriptiv), rularea aleasă a convers în 37 de iterații; inerția a scăzut de la 2.664,1 la 979,0. Valorile sunt pe meci:

| Grup | Goluri marcate | Goluri primite | Șuturi pe poartă | Șuturi pe poartă primite | Puncte | Acasă − deplasare | Profiluri | Cele mai tipice |
|---|---|---|---|---|---|---|---|---|
| 0 — elita | 2,50 | 0,89 | 6,83 | 3,40 | 2,33 | 0,46 | 36 | Barcelona 2018/19, 2017/18, 2013/14 |
| 1 — jumătatea de sus | 1,48 | 1,09 | 4,47 | 3,74 | 1,67 | 0,53 | 101 | Athletic 2015/16, Villarreal 2021/22, 2013/14 |
| 2 — jumătatea de jos, puternică acasă | 1,19 | 1,43 | 4,14 | 4,59 | 1,22 | 0,91 | 125 | Getafe 2023/24, Espanyol 2011/12, Las Palmas 2015/16 |
| 3 — slabă peste tot | 1,06 | 1,55 | 3,74 | 4,76 | 1,06 | 0,29 | 138 | Granada 2012/13, Valladolid 2009/10, Girona 2025/26 |

- Elita cuprinde 18 sezoane ale Barcelonei, 17 ale Realului Madrid și unul al lui Atlético Madrid: duopolul din La Liga apare ca grup separat.
- Grupul 1 este dominat de Atlético Madrid (17 sezoane), Villarreal (13), Athletic (12) și Sevilla (11).
- Cele două grupuri din jumătatea de jos au puncte apropiate (1,22 și 1,06), dar diferă prin dependența de terenul propriu: grupul 2 câștigă cu 0,91 puncte pe meci mai mult acasă, grupul 3 doar cu 0,29. Grupul 3 este slab și acasă.

### 8.5. Grupurile momentane în sezoanele de evaluare

Pe cele 16 sezoane de evaluare (2010/11–2025/26, 320 de echipe-sezon), grupurile momentane sunt: 30 în grupul 0, 100 în grupul 1, 64 în grupul 2, 78 în grupul 3 și 48 de echipe promovate. Dintre echipele care au grup în două sezoane consecutive, 57% păstrează același grup.

De exemplu, pentru sezonul 2025/26 (calculat doar din sezoanele 2006/07–2024/25):
- grupul 0: Barcelona, Real Madrid;
- grupul 1: Athletic, Atlético Madrid, Betis, Rayo Vallecano, Villarreal;
- grupul 2: Celta, Espanyol, Osasuna, Valencia;
- grupul 3: Alavés, Getafe, Girona, Mallorca, Sevilla, Real Sociedad;
- promovate: Elche, Levante, Oviedo.

## 9. Complexitate

Notații: $n$ — numărul de puncte, $d$ — numărul de caracteristici, $k$ — numărul de grupuri, $T$ — numărul de iterații, $R$ — numărul de porniri, $S$ — numărul de semințe comparate.

| Operație | Timp | Memorie |
|---|---|---|
| Standardizarea | O(n d) | O(n d) |
| Centrele k-means++ (Ec. 5) | O(n k d) | O(n) |
| O iterație Lloyd (Ec. 2–3, 7) | O(n k d) | O(n k) |
| O rulare completă | O(T n k d) | O(n k + n d) |
| K-Means cu $R$ porniri | O(R · T n k d) | O(n k + n d) |
| Silhouette (Ec. 8) | O(n² d) | O(n²) |
| Indicele Rand pentru două grupări | O(n²) | O(n²) |
| Stabilitatea pe $S$ semințe | O(S² n² + S R T n k d) | O(n²) |
| Grupurile momentane ale unui sezon | O(R · T n k d) pe profilurile sezoanelor anterioare | O(n d) |

Pentru $n = 400$, $d = 6$ și $k = 4$, întreaga comparație (șapte valori ale lui $k$, câte 10 semințe a 10 porniri, pe 80 și pe 400 de profiluri) durează aproximativ 2 s.

## 10. Ipoteze

- Profilul de șase indicatori descrie suficient tipul unei echipe într-un sezon.
- După standardizare, toate caracteristicile sunt la fel de importante.
- Grupurile sunt aproximativ „rotunde” și de mărimi comparabile, cum presupune distanța euclidiană.
- Profilul din sezonul anterior descrie suficient de bine o echipă la începutul sezonului următor.

## 11. Limitări

- Valorile silhouette mici arată că granițele dintre grupuri sunt vagi; echipele de la granițe își pot schimba grupul ușor.
- Pe toate sezoanele, cele două grupuri din jumătatea de jos se suprapun parțial (stabilitate 0,832).
- În sezoanele de calibrare, elita are doar 3 profiluri; grupurile momentane din primele sezoane sunt calculate din puține date (2007/08: doar din cele 20 de profiluri ale sezonului 2006/07).
- Doar 57% dintre echipe păstrează grupul de la un sezon la altul: profilul anterior descrie imperfect sezonul următor (transferuri, antrenori noi).
- Echipele promovate formează un singur grup, deși pot fi foarte diferite între ele.
- K-Means poate găsi un minim local; cele 10 porniri reduc riscul, dar nu îl elimină.

## 12. Exemple din teste

Testele sunt în `tests/test_kmeans.py`, `tests/test_team_profiles.py`, `tests/test_team_clustering.py` și `tests/test_kmeans_selection.py`.

- Punctele (0, 0), (0, 1), (10, 10), (10, 11), fără standardizare: centrele sunt (0; 0,5) și (10; 10,5), iar inerția este 1.
- Grup gol: punctele 0, 1, 10, toate în grupul 0 (media 11/3); grupul gol primește punctul 10, cel mai îndepărtat.
- Inerția nu crește la nicio iterație, chiar pornind de la centre proaste; trei grupuri simulate bine separate sunt regăsite exact, cu centrele lor.
- k-means++ nu alege de două ori același punct, chiar dacă există puncte duplicate; $k = 1$ dă media tuturor punctelor, iar $k = n$ dă inerția 0.
- Silhouette pentru 0, 1, 10, 11 cu grupurile {0, 1} și {10, 11}: 0,899749; un punct singur în grupul lui are 0.
- Indicele Rand: grupări identice cu alte numere dau 1; [0, 0, 1, 1] față de [0, 1, 0, 1] dă 2/6.
- Profil calculat de mână: Alpha are 4/6 goluri marcate și 2/6 primite pe meci, 11/6 puncte pe meci, iar diferența acasă − deplasare este 2 − 5/3.
- Fără scurgere de informații: inversarea tuturor rezultatelor din sezonul S nu schimbă grupurile momentane ale lui S; echipa promovată nu primește grup.

## 13. Rolul în PitchSense

- În interfață (analiza unei echipe), K-Means arată tipul echipei în fiecare sezon și echipele cu profil asemănător.
- În evaluare (Faza 10), grupurile momentane permit răspunsul la întrebarea „unde funcționează bine fiecare metodă”, de exemplu în meciurile elită contra echipă slabă sau între echipe din același grup.
- Grupurile nu sunt folosite ca intrări pentru predicții.

## 14. Surse

- MacQueen, J. (1967). Some methods for classification and analysis of multivariate observations. *Proceedings of the Fifth Berkeley Symposium on Mathematical Statistics and Probability*, 1, 281–297.
- Lloyd, S. P. (1982). Least squares quantization in PCM. *IEEE Transactions on Information Theory*, 28(2), 129–137.
- Arthur, D., & Vassilvitskii, S. (2007). k-means++: The advantages of careful seeding. *Proceedings of the 18th Annual ACM-SIAM Symposium on Discrete Algorithms*, 1027–1035.
- Rousseeuw, P. J. (1987). Silhouettes: A graphical aid to the interpretation and validation of cluster analysis. *Journal of Computational and Applied Mathematics*, 20, 53–65.
- Rand, W. M. (1971). Objective criteria for the evaluation of clustering methods. *Journal of the American Statistical Association*, 66(336), 846–850.

Codul a fost scris pornind de la formulele de mai sus, nu copiat dintr-o implementare existentă. `sklearn.cluster.KMeans` nu este folosit.

## 15. Reproducere

```bash
python -m app.data.build_database
python -m app.evaluation.kmeans_selection
```
