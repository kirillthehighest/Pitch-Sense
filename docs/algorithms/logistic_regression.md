# Regresia logistică (multinomială)

Acest document descrie implementarea noastră a regresiei logistice multinomiale din `app/algorithms/logistic_regression.py` și felul în care este folosită în PitchSense. Modelul este scris de la zero cu NumPy, fără biblioteci de învățare automată. Ecuațiile sunt numerotate la fel ca în cod.

## 1. Problema rezolvată

Regresia logistică clasifică fiecare meci într-una dintre trei clase: victoria gazdelor (H), egal (D) sau victoria oaspeților (A). Pentru fiecare meci oferă probabilitatea fiecărei clase, pornind de la câțiva indicatori numerici calculați din meciurile anterioare.

## 2. De ce este potrivită

- Rezultatul unui meci are exact trei categorii, iar regresia logistică multinomială (softmax) le modelează direct, cu probabilități a căror sumă este 1.
- Combină mai mulți indicatori (rating Elo, puncte, goluri, formă, șuturi pe poartă) și învață din date cât contează fiecare.
- Ponderile învățate se pot interpreta: arată în ce direcție și cât de mult împinge fiecare indicator probabilitățile.
- Funcția de pierdere este convexă, deci antrenarea prin gradient descent ajunge la singura soluție optimă, indiferent de punctul de pornire.

## 3. Principiul matematic

Notații: $n$ — numărul de exemple de antrenare, $d$ — numărul de caracteristici, $C = 3$ — numărul de clase.

**Matricea caracteristicilor.** $X$ are $n$ rânduri și $d$ coloane. Fiecare coloană este standardizată cu media și abaterea standard ale datelor de antrenare: $x' = (x - \text{medie}) / \text{abatere}$. $\tilde{X}$ este $X$ cu o primă coloană de 1, pentru termenii liberi (bias).

**Ținta (Ec. 1).** $Y$ are $n$ rânduri și $C$ coloane: $Y_{ic} = 1$ dacă exemplul $i$ aparține clasei $c$, altfel 0 (codificare „one-hot”). Ordinea claselor este H = 0, D = 1, A = 2.

**Parametrii.** $W$ are $d + 1$ rânduri și $C$ coloane: rândul 0 conține termenii liberi, iar fiecare coloană corespunde unei clase.

**Scorurile (Ec. 2):** $Z = \tilde{X} W$.

**Probabilitățile (Ec. 3, softmax):**

$$P_{ic} = \frac{e^{Z_{ic}}}{\sum_{k} e^{Z_{ik}}}$$

Înainte de exponențiere se scade maximul fiecărui rând. Rezultatul nu se schimbă, dar valorile mari nu mai produc depășiri numerice.

**Pierderea (Ec. 4):** entropia încrucișată medie plus penalizarea L2, fără termenii liberi:

$$L(W) = -\frac{1}{n} \sum_{i} \ln P_{i, y_i} + \frac{\lambda}{2} \sum_{j \ge 1} \sum_{c} W_{jc}^2$$

Logaritmul probabilităților se calculează direct ca $Z - \ln \sum_k e^{Z_k}$, deci nu apare niciodată $\ln 0$.

**Gradientul (Ec. 5):**

$$\nabla L(W) = \frac{1}{n} \tilde{X}^\top (P - Y) + \lambda W, \quad \text{fără termenul } \lambda W \text{ pentru rândul 0}$$

**Actualizarea (Ec. 6, gradient descent):** $W \leftarrow W - \eta \, \nabla L(W)$, cu pasul

$$\eta = \frac{1}{\tfrac{1}{2}\, \ell_{\max}\!\left(\tilde{X}^\top \tilde{X} / n\right) + \lambda}$$

unde $\ell_{\max}$ este cea mai mare valoare proprie. Numitorul este o margine superioară a curburii pierderii (Böhning, 1992). Cu acest pas, fiecare iterație micșorează pierderea sau o lasă neschimbată, deci rata de învățare nu trebuie aleasă manual.

**Oprirea (Ec. 7):** antrenarea se oprește când pierderea scade cu mai puțin de $10^{-8} \cdot |L|$ sau după 10.000 de iterații. Istoricul pierderii este păstrat.

**Identificabilitate.** Dacă adunăm același număr la toate cele trei coloane ale unui rând din $W$, probabilitățile softmax nu se schimbă. De aceea ponderile se compară și se interpretează după centrarea fiecărui rând (scăderea mediei celor trei valori). Pornind de la ponderi zero, gradient descent păstrează automat această centrare.

**O clasă fără exemple.** Dacă datele de antrenare nu conțin nicio clasă $c$, termenul liber al acelei clase poate scădea la nesfârșit, iar pierderea nu are minim. În acest caz antrenarea este refuzată cu o eroare.

## 4. Intrări

Cele cinci caracteristici ale unui meci sunt diferențe „gazde minus oaspeți”, calculate doar din meciurile dinaintea zilei meciului (`app/prediction/logistic_features.py`):

| Caracteristică | Calcul |
|---|---|
| `elo_difference` | ratingul Elo al gazdelor minus cel al oaspeților, înaintea zilei meciului (Faza 3) |
| `points_per_match_difference` | puncte pe meci: gazdele în ultimele 19 meciuri de acasă, oaspeții în ultimele 19 din deplasare |
| `goal_difference_per_match_difference` | golaverajul pe meci, cu aceleași ferestre |
| `form_difference` | puncte pe meci în ultimele 5 meciuri, indiferent de teren |
| `shots_on_target_difference` | șuturi pe poartă proprii minus ale adversarilor, pe meci, cu ferestrele de 19 meciuri |

O echipă fără istoricul necesar primește media ligii din ultimele 380 de meciuri, separat pentru gazde și oaspeți, astfel încât avantajul terenului propriu se păstrează. De exemplu, punctele pe meci ale gazdelor sunt $3 \cdot P(H) + P(D)$.

**Două caracteristici în plus (Faza 23)**, adăugate doar în ligile în care calibrarea le alege (secțiunea 7.3):

| Caracteristică | Calcul |
|---|---|
| `elo_gap` | $|$diferența Elo$|$: cât de apropiate sunt echipele, indiferent care e mai puternică |
| `expected_goals_difference` | $\lambda_h - \lambda_a$ ale modelului Poisson pentru meci, din meciurile dinaintea zilei lui; până când modelul Poisson poate prezice, golurile gazdelor minus ale oaspeților pe meci în ligă |

Modelul este liniar în caracteristici, iar cele cinci de bază sunt diferențe „gazde minus oaspeți”: cu ele, probabilitatea egalului poate urma doar avantajul uneia dintre echipe. `elo_gap` îi permite să crească atunci când echipele sunt apropiate, oricare ar fi mai puternică. `expected_goals_difference` aduce în model estimarea golurilor, cu forțele de atac și de apărare ale modelului Poisson.

Alte intrări: rezultatele meciurilor anterioare (clasele), puterea penalizării $\lambda$, toleranța și numărul maxim de iterații.

## 5. Ieșiri

- probabilitățile $(P(H), P(D), P(A))$ ale fiecărui meci, în această ordine, în formatul comun al predicțiilor;
- ponderile $W$, statisticile de standardizare și istoricul pierderii fiecărui model antrenat;
- numărul de iterații și dacă antrenarea a convers.

## 6. Pseudocod

```
ANTRENEAZĂ(X, y, λ, toleranță, maxim_iterații, W_inițial):
    dacă o clasă nu apare în y: eroare                         ▷ pierderea nu ar avea minim
    medie, abatere ← media și abaterea standard a fiecărei coloane din X (abatere 0 → 1)
    X~ ← [1, (X − medie) / abatere]
    Y ← ONE_HOT(y)                                              ▷ Ec. 1
    W ← W_inițial sau matricea zero
    η ← 1 / (½ · cea_mai_mare_valoare_proprie(X~ᵀ X~ / n) + λ)
    L ← PIERDERE(W)
    repetă de cel mult maxim_iterații ori:
        P ← SOFTMAX(X~ W)                                        ▷ Ec. 2–3
        G ← X~ᵀ (P − Y) / n;  G[1:] ← G[1:] + λ · W[1:]          ▷ Ec. 5
        W ← W − η · G                                            ▷ Ec. 6
        L_nou ← PIERDERE(W)                                      ▷ Ec. 4
        dacă L − L_nou < toleranță · |L|: oprește               ▷ Ec. 7
        L ← L_nou
    returnează W, medie, abatere

PREDICȚII_SĂPTĂMÂNALE(meciuri, λ):
    antrenare ← listă vidă;  W ← nimic
    pentru fiecare săptămână calendaristică s, în ordine:
        dacă antrenare are ≥ 100 de meciuri și toate cele trei rezultate:
            W, medie, abatere ← ANTRENEAZĂ(antrenare, λ, W_inițial = W)
            prezice fiecare meci din s cu SOFTMAX([1, (x − medie) / abatere] · W)
        adaugă meciurile din s la antrenare                     ▷ abia după predicții
```

## 7. Detalii de implementare

### 7.1. Fișiere

| Fișier | Conținut |
|---|---|
| `app/algorithms/logistic_regression.py` | Ec. 1–7: standardizarea, codificarea one-hot, softmax, pierderea, gradientul, antrenarea și modelul antrenat. Folosește doar NumPy și biblioteca standard Python. |
| `app/prediction/logistic_features.py` | Cele cinci caracteristici ale fiecărui meci și, după setări, cele două în plus, din datele dinaintea zilei lui; `feature_names` dă lista lor. |
| `app/prediction/logistic_predictions.py` | Reantrenarea săptămânală și predicțiile; valorile alese sunt implicite. |
| `app/evaluation/logistic_calibration.py` | Alegerea lui $\lambda$ și a caracteristicilor în plus: `python -m app.evaluation.logistic_calibration`. |

### 7.2. Valorile parametrilor

| Parametru | Valoare | Cum a fost ales |
|---|---|---|
| $\lambda$ (L2) | 0,1 | calibrare (secțiunea 7.3) |
| caracteristicile în plus | `elo_gap` și `expected_goals_difference` | calibrare (secțiunea 7.3), din Faza 23 |
| toleranța de oprire | $10^{-8}$ (relativă) | valoare implicită documentată |
| numărul maxim de iterații | 10.000 | valoare implicită documentată; în practică nu se atinge niciodată (maximum 79) |
| meciuri minime de antrenare | 100 | valoare implicită; prima predicție este pe 25 noiembrie 2006, în sezonul de încălzire |
| reantrenare | o dată pe săptămână (luni), cu fereastră care crește | decizia echipei |
| ferestrele caracteristicilor | 19 meciuri acasă/deplasare, 5 pentru formă, 380 pentru liga | un sezon de meciuri acasă (sau în deplasare); forma din Faza 2; un sezon al ligii |

Valorile sunt cele ale La Liga. Fiecare ligă își alege $\lambda$ și caracteristicile în plus pe propriile sezoane de calibrare (rulare din 2026-10-16: toate ligile $\lambda = 0{,}1$; Premier League și Serie A adaugă `expected_goals_difference`, Bundesliga și Ligue 1 rămân la cele cinci), folosește diferența Elo calculată cu propriul Elo și golurile așteptate ale propriului model Poisson, iar ferestrele urmează mărimea ligii: 17 meciuri acasă/deplasare și 306 pentru liga la 18 echipe (`docs/leagues.md`, secțiunea 2). Până în Faza 23, Premier League avea $\lambda = 0{,}01$.

### 7.3. Calibrarea lui λ și a caracteristicilor

Modelul a fost rulat doar pe sezonul de încălzire 2006/07 și pe sezoanele de calibrare 2007/08–2009/10; sezoanele de evaluare nu sunt citite. Pentru fiecare valoare $\lambda \in \{0; 0{,}001; 0{,}01; 0{,}1; 1\}$ și fiecare set de caracteristici (cele cinci de bază, plus niciuna, una sau ambele caracteristici din Faza 23; 20 de alegeri) s-a calculat pierderea logaritmică (media lui $-\ln P(\text{rezultatul real})$) pe cele 1.140 de meciuri de calibrare. Este chiar mărimea pe care modelul o minimizează la antrenare. Diferența Elo folosește Elo-ul ales de calibrarea lui ($K = 10$, $H = 80$, cu ponderea golurilor), iar golurile așteptate modelul Poisson ales de calibrarea lui. Rulare din 2026-10-16:

| λ | Caracteristici în plus | Pierderea logaritmică |
|---|---|---|
| **0,1** | **`elo_gap`, `expected_goals_difference`** | **0,98299** |
| 0,1 | `elo_gap` | 0,98342 |
| 0,1 | `expected_goals_difference` | 0,98372 |
| 0,01 | `expected_goals_difference` | 0,98400 |
| 0,1 | niciuna | 0,98435 |

Până în Faza 23, cu cele cinci caracteristici și Elo-ul de atunci ($K = 15$, $H = 80$), cea mai bună valoare a fost tot $\lambda = 0{,}1$, cu 0,98627. Ca referință, o predicție constantă cu frecvențele rezultatelor din sezonul de încălzire are 1,04696; regresia logistică o reduce acum cu 6,1%. Valoarea aleasă pentru $\lambda$ este în interiorul grilei.

### 7.4. Diagnostic pe sezoanele de calibrare

Cu setările La Liga ($\lambda = 0{,}1$, șapte caracteristici), pe cele 1.140 de meciuri din 2007/08–2009/10 (rulare din 2026-10-16):

- Media probabilităților prezise este 48,4% / 23,4% / 28,1%, față de rezultatele reale 49,1% / 23,2% / 27,6%.
- Probabilitatea egalului variază între 6,0% și 44,0% (între 10,9% și 37,9% cu cele cinci caracteristici), iar cea a victoriei gazdelor între 12,9% și 89,6%.
- Egalul este rezultatul cel mai probabil la doar 0,3% dintre meciuri (victoria gazdelor la 79,6%, a oaspeților la 20,1%). Chiar când egalul are o probabilitate mare, una dintre victorii are de obicei una și mai mare. Acest lucru contează pentru acuratețe: un model care alege mereu rezultatul cel mai probabil aproape nu prezice niciodată egaluri.
- Toate cele 106 reantrenări săptămânale au convers, cu o mediană de 33 de iterații (maximum 57), datorită pornirii de la ponderile săptămânii anterioare.

**Antrenarea pe toate cele 1.519 meciuri de încălzire și calibrare**, pornind de la ponderi zero, a convers în 74 de iterații. Pierderea a scăzut astfel:

| Iterația | 0 | 1 | 5 | 10 | 50 | 74 (final) |
|---|---|---|---|---|---|---|
| Pierderea | 1,09861 | 1,04111 | 1,00981 | 1,00144 | 0,99892 | 0,99892 |

La iterația 0, toate probabilitățile sunt 1/3, iar pierderea este $\ln 3 = 1{,}09861$.

**Ponderile învățate**, centrate, pentru o creștere de o abatere standard a fiecărei caracteristici:

| Caracteristică (abaterea standard) | H | D | A |
|---|---|---|---|
| termenul liber | +0,421 | −0,255 | −0,166 |
| diferența Elo (93,6 puncte) | +0,185 | −0,044 | −0,141 |
| puncte pe meci (0,75) | +0,004 | +0,043 | −0,047 |
| golaveraj pe meci (1,02) | −0,011 | +0,027 | −0,016 |
| formă (0,94) | +0,071 | +0,002 | −0,073 |
| șuturi pe poartă (2,11) | +0,106 | −0,017 | −0,089 |
| distanța Elo, $|$diferența Elo$|$ (62,6 puncte) | +0,042 | −0,073 | +0,030 |
| diferența golurilor așteptate (0,49) | +0,095 | −0,047 | −0,048 |

Semnele diferențelor sunt cele așteptate: o valoare mai mare favorizează gazdele și defavorizează oaspeții (golaverajul are o pondere aproape nulă). Diferența Elo are cea mai mare influență, urmată de șuturile pe poartă și de golurile așteptate. Termenul liber pozitiv pentru H reprezintă avantajul terenului propriu. Distanța Elo face exact ce i se cere: cu cât echipele sunt mai departe una de alta, cu atât egalul e mai puțin probabil (−0,073). Punctele și golaverajul au ponderi mici, pentru că informația lor se suprapune cu cea a ratingului Elo: corelațiile diferenței Elo cu celelalte caracteristici sunt 0,64, 0,72, 0,56, 0,62, 0,00 (distanța) și 0,86 (golurile așteptate).

### 7.5. Modificare în Faza 23: două caracteristici în plus

Echipa a cerut mai multe caracteristici. Cele două de mai sus au fost adăugate ca opțiuni ale grilei de calibrare: La Liga le-a ales pe amândouă, Premier League și Serie A doar golurile așteptate, iar Bundesliga și Ligue 1 niciuna. Pe sezoanele de evaluare (2010/11–2025/26), comparat meci cu meci cu modelul de dinainte, scorul Brier s-a schimbat cu +0,0014 (Premier League, o înrăutățire reală; acolo s-au schimbat și $\lambda$, de la 0,01 la 0,1, și Elo-ul din care vine diferența Elo), −0,0015 (La Liga, reală), −0,0006 (Serie A), −0,0004 (Bundesliga, reală, doar din noul Elo) și 0 (Ligue 1, neschimbată). Pe toate ligile la un loc, −0,0002, cu intervalul [−0,0005; +0,0001]: nicio schimbare reală. Regresia logistică rămâne cel mai bun model în patru ligi (`docs/leagues.md`).

## 8. Complexitate

Notații: $n$ — numărul de exemple de antrenare, $d$ — numărul de caracteristici (5 până la 7), $C$ — numărul de clase (3), $T$ — numărul de iterații, $R$ — numărul de reantrenări.

| Operație | Timp | Memorie |
|---|---|---|
| Standardizarea | O(n d) | O(n d) |
| Pasul $\eta$ (valoarea proprie a unei matrice $(d+1) \times (d+1)$) | O(n d² + d³) | O(d²) |
| O iterație (scoruri, softmax, gradient, pierdere) | O(n d C) | O(n C) |
| Antrenarea completă | O(T · n d C + n d² + d³) | O(n d + n C) |
| Predicția unui meci | O(d C) | O(C) |
| Toate predicțiile, cu reantrenare săptămânală | O(R · T · n d C) | O(n d) |

Pe datele reale ale La Liga, cu $R = 698$ reantrenări și $T \le 79$ iterații datorită pornirii de la ponderile anterioare, toate cele 7.490 de predicții se calculează în aproximativ 7,4 s (cu rularea Poisson pentru golurile așteptate), iar calibrarea pe cele 20 de alegeri, cu calibrarea Elo și Poisson de care are nevoie, în aproximativ 60 s (rulare din 2026-10-16).

## 9. Ipoteze

- Logaritmul raportului dintre probabilitățile a două rezultate este o funcție liniară de caracteristici.
- Meciurile sunt independente între ele, iar relația dintre caracteristici și rezultat se schimbă lent, deci un model antrenat pe meciurile trecute se aplică și săptămâna următoare.
- Caracteristicile (cele cinci de bază și cele alese în plus) descriu suficient diferența de forță dintre echipe.

## 10. Limitări

- Modelul este liniar în caracteristici, deci nu poate surprinde direct efecte precum „egalurile sunt mai frecvente când echipele sunt foarte apropiate” decât printr-o caracteristică făcută anume (distanța Elo, aleasă doar în La Liga).
- Caracteristicile sunt corelate, deci ponderile individuale trebuie interpretate cu grijă: L2 le stabilizează, dar nu le face independente.
- Folosește ratingul Elo ca intrare și, în trei ligi, golurile așteptate ale modelului Poisson, deci nu este independentă de celelalte două modele. Acest lucru trebuie menționat în compararea algoritmilor.
- Egalul nu este aproape niciodată rezultatul cel mai probabil, chiar dacă probabilitatea lui este realistă.
- Echipele fără istoric primesc media ligii, deși echipele promovate sunt de obicei mai slabe.
- Calibrarea folosește doar trei sezoane, iar grila lui $\lambda$ are doar cinci valori. Cu 20 de alegeri pe 1.140 de meciuri, diferențele mici dintre seturile de caracteristici pot fi întâmplătoare (secțiunea 7.5).

## 11. Exemple din teste

Testele sunt în `tests/test_logistic.py`, `tests/test_logistic_features.py`, `tests/test_logistic_predictions.py` și `tests/test_logistic_calibration.py`.

- Softmax: $(0, \ln 2, \ln 3) \to (1/6, 2/6, 3/6)$; rămâne exact și pentru scoruri de ±1000.
- Cu ponderi zero, pierderea este $\ln 3$, iar gradientul termenilor liberi este $1/3$ minus frecvența fiecărei clase.
- Gradientul din Ec. 5 coincide cu o estimare numerică (diferențe finite) pentru toate cele 15 ponderi.
- Pierderea nu crește la nicio iterație; pe 20.000 de meciuri simulate, antrenarea a convers în 44 de iterații și a regăsit ponderile reale cu o eroare sub 0,1.
- Cu o singură caracteristică, softmax poate face egalul cel mai probabil între două extreme.
- O clasă fără exemple de antrenare este refuzată cu o eroare.
- Caracteristici calculate de mână: pentru A acasă contra C, diferențele sunt 0 (puncte), −1 (golaveraj), −0,5 (formă) și +2 (șuturi pe poartă); pentru o echipă nouă, valorile ei sunt mediile ligii, de exemplu 1,75 puncte pe meci acasă.
- Caracteristicile în plus: distanța Elo este valoarea absolută a diferenței Elo; golurile așteptate sunt exact $\lambda_h - \lambda_a$ ale modelului Poisson, iar înainte ca acesta să poată prezice (fără goluri ale gazdelor în ligă), golurile gazdelor minus ale oaspeților pe meci; numele necunoscute sau golurile așteptate fără setări Poisson sunt refuzate; predicțiile Poisson date gata calculate dau aceleași caracteristici; un set de caracteristici din calibrare are pierderea modelului rulat cu acel set.
- Fiecare săptămână este antrenată doar pe meciurile dinaintea zilei de luni; schimbarea rezultatului unui meci nu modifică nicio caracteristică sau predicție din ziua lui sau dinainte, nici cu caracteristicile în plus.

## 12. Rolul în PitchSense

- Este al treilea algoritm de predicție: probabilitățile lui vor fi comparate cu cele ale ratingului Elo și ale modelului Poisson (fazele 8–10).
- Arată cum se pot combina mai mulți indicatori într-un singur model și cât contează fiecare.
- Ponderile, istoricul pierderii și numărul de iterații pot fi afișate în interfață pentru a explica modelul.

Exemplu pentru un meci din sezonul 2025/26 (Real Madrid – Barcelona, 26 octombrie 2025), cu modelul antrenat pe cele 7.308 meciuri anterioare săptămânii, cu setările din Faza 23: caracteristici (Elo +5,0; puncte +0,32; golaveraj −0,21; formă 0,0; șuturi pe poartă +2,05; distanța Elo 5,0; golurile așteptate +0,29); probabilități 43,2% / 28,4% / 28,4%. Scorul real a fost 2–1. Exemplul ilustrează forma predicției; evaluarea modelului se face în fazele 8–10.

## 13. Surse

- Bishop, C. M. (2006). *Pattern Recognition and Machine Learning*. Springer. Secțiunea 4.3.4, regresia logistică multiclasă.
- Böhning, D. (1992). Multinomial logistic regression algorithm. *Annals of the Institute of Statistical Mathematics*, 44(1), 197–200. Marginea superioară a curburii folosită pentru pasul $\eta$.
- Boyd, S., & Vandenberghe, L. (2004). *Convex Optimization*. Cambridge University Press. Gradient descent pentru funcții convexe.
- Hvattum, L. M., & Arntzen, H. (2010). Using ELO ratings for match result prediction in association football. *International Journal of Forecasting*, 26(3), 460–470. Ratingurile Elo folosite ca intrare într-un model de regresie.

Codul a fost scris pornind de la formulele de mai sus, nu copiat dintr-o implementare existentă. `sklearn.linear_model.LogisticRegression` nu este folosit.

## 14. Reproducere

```bash
python -m app.data.build_database
python -m app.evaluation.logistic_calibration
```
