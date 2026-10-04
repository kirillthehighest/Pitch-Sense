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
| `app/prediction/logistic_features.py` | Cele cinci caracteristici ale fiecărui meci, din datele dinaintea zilei lui. |
| `app/prediction/logistic_predictions.py` | Reantrenarea săptămânală și predicțiile; valorile alese sunt implicite. |
| `app/evaluation/logistic_calibration.py` | Alegerea lui $\lambda$: `python -m app.evaluation.logistic_calibration`. |

### 7.2. Valorile parametrilor

| Parametru | Valoare | Cum a fost ales |
|---|---|---|
| $\lambda$ (L2) | 0,1 | calibrare (secțiunea 7.3) |
| toleranța de oprire | $10^{-8}$ (relativă) | valoare implicită documentată |
| numărul maxim de iterații | 10.000 | valoare implicită documentată; în practică nu se atinge niciodată (maximum 65) |
| meciuri minime de antrenare | 100 | valoare implicită; prima predicție este pe 25 noiembrie 2006, în sezonul de încălzire |
| reantrenare | o dată pe săptămână (luni), cu fereastră care crește | decizia echipei |
| ferestrele caracteristicilor | 19 meciuri acasă/deplasare, 5 pentru formă, 380 pentru liga | un sezon de meciuri acasă (sau în deplasare); forma din Faza 2; un sezon al ligii |

### 7.3. Calibrarea lui λ

Modelul a fost rulat doar pe sezonul de încălzire 2006/07 și pe sezoanele de calibrare 2007/08–2009/10; sezoanele de evaluare nu sunt citite. Pentru fiecare valoare $\lambda \in \{0; 0{,}001; 0{,}01; 0{,}1; 1\}$ s-a calculat pierderea logaritmică (media lui $-\ln P(\text{rezultatul real})$) pe cele 1.140 de meciuri de calibrare. Este chiar mărimea pe care modelul o minimizează la antrenare. Rulare din 2026-10-04:

| λ | Pierderea logaritmică |
|---|---|
| **0,1** | **0,98627** |
| 0,01 | 0,98687 |
| 0,001 | 0,98749 |
| 0 | 0,98758 |
| 1 | 1,00363 |

Ca referință, o predicție constantă cu frecvențele rezultatelor din sezonul de încălzire are 1,04696; regresia logistică o reduce cu 5,8%. Valoarea aleasă este în interiorul grilei.

### 7.4. Diagnostic pe sezoanele de calibrare

Cu $\lambda = 0{,}1$, pe cele 1.140 de meciuri din 2007/08–2009/10:

- Media probabilităților prezise este 47,5% / 24,1% / 28,3%, față de rezultatele reale 49,1% / 23,2% / 27,6%.
- Probabilitatea egalului variază între 10,9% și 37,9%, iar cea a victoriei gazdelor între 10,8% și 83,2%.
- Egalul este rezultatul cel mai probabil la doar 0,1% dintre meciuri (victoria gazdelor la 78,8%, a oaspeților la 21,1%). Chiar când egalul are o probabilitate mare, una dintre victorii are de obicei una și mai mare. Acest lucru contează pentru acuratețe: un model care alege mereu rezultatul cel mai probabil aproape nu prezice niciodată egaluri.
- Toate cele 106 reantrenări săptămânale au convers, cu o mediană de 25 de iterații (maximum 40), datorită pornirii de la ponderile săptămânii anterioare.

**Antrenarea pe toate cele 1.519 meciuri de încălzire și calibrare**, pornind de la ponderi zero, a convers în 52 de iterații. Pierderea a scăzut astfel:

| Iterația | 0 | 1 | 5 | 10 | 50 | 52 (final) |
|---|---|---|---|---|---|---|
| Pierderea | 1,09861 | 1,04017 | 1,00941 | 1,00361 | 1,00256 | 1,00256 |

La iterația 0, toate probabilitățile sunt 1/3, iar pierderea este $\ln 3 = 1{,}09861$.

**Ponderile învățate**, centrate, pentru o creștere de o abatere standard a fiecărei caracteristici:

| Caracteristică (abaterea standard) | H | D | A |
|---|---|---|---|
| termenul liber | +0,417 | −0,249 | −0,168 |
| diferența Elo (89,6 puncte) | +0,205 | −0,049 | −0,156 |
| puncte pe meci (0,75) | +0,017 | +0,034 | −0,051 |
| golaveraj pe meci (1,02) | +0,028 | +0,009 | −0,037 |
| formă (0,94) | +0,071 | +0,003 | −0,074 |
| șuturi pe poartă (2,11) | +0,127 | −0,026 | −0,101 |

Toate semnele sunt cele așteptate: o valoare mai mare favorizează gazdele și defavorizează oaspeții. Diferența Elo are cea mai mare influență, urmată de șuturile pe poartă. Termenul liber pozitiv pentru H reprezintă avantajul terenului propriu. Punctele și golaverajul au ponderi mici, pentru că informația lor se suprapune cu cea a ratingului Elo: corelațiile diferenței Elo cu celelalte patru caracteristici sunt 0,66, 0,71, 0,58 și 0,60.

## 8. Complexitate

Notații: $n$ — numărul de exemple de antrenare, $d$ — numărul de caracteristici (5), $C$ — numărul de clase (3), $T$ — numărul de iterații, $R$ — numărul de reantrenări.

| Operație | Timp | Memorie |
|---|---|---|
| Standardizarea | O(n d) | O(n d) |
| Pasul $\eta$ (valoarea proprie a unei matrice $(d+1) \times (d+1)$) | O(n d² + d³) | O(d²) |
| O iterație (scoruri, softmax, gradient, pierdere) | O(n d C) | O(n C) |
| Antrenarea completă | O(T · n d C + n d² + d³) | O(n d + n C) |
| Predicția unui meci | O(d C) | O(C) |
| Toate predicțiile, cu reantrenare săptămânală | O(R · T · n d C) | O(n d) |

Pe datele reale, cu $R = 698$ reantrenări și $T \le 65$ iterații datorită pornirii de la ponderile anterioare, toate cele 7.490 de predicții se calculează în aproximativ 6 s, iar calibrarea în aproximativ 5 s.

## 9. Ipoteze

- Logaritmul raportului dintre probabilitățile a două rezultate este o funcție liniară de caracteristici.
- Meciurile sunt independente între ele, iar relația dintre caracteristici și rezultat se schimbă lent, deci un model antrenat pe meciurile trecute se aplică și săptămâna următoare.
- Cele cinci caracteristici descriu suficient diferența de forță dintre echipe.

## 10. Limitări

- Modelul este liniar în caracteristici, deci nu poate surprinde direct efecte precum „egalurile sunt mai frecvente când echipele sunt foarte apropiate” decât prin combinația celor trei clase.
- Caracteristicile sunt corelate, deci ponderile individuale trebuie interpretate cu grijă: L2 le stabilizează, dar nu le face independente.
- Folosește ratingul Elo ca intrare, deci nu este complet independentă de algoritmul Elo. Acest lucru trebuie menționat în compararea algoritmilor.
- Egalul nu este aproape niciodată rezultatul cel mai probabil, chiar dacă probabilitatea lui este realistă.
- Echipele fără istoric primesc media ligii, deși echipele promovate sunt de obicei mai slabe.
- Calibrarea folosește doar trei sezoane, iar grila lui $\lambda$ are doar cinci valori.

## 11. Exemple din teste

Testele sunt în `tests/test_logistic.py`, `tests/test_logistic_features.py`, `tests/test_logistic_predictions.py` și `tests/test_logistic_calibration.py`.

- Softmax: $(0, \ln 2, \ln 3) \to (1/6, 2/6, 3/6)$; rămâne exact și pentru scoruri de ±1000.
- Cu ponderi zero, pierderea este $\ln 3$, iar gradientul termenilor liberi este $1/3$ minus frecvența fiecărei clase.
- Gradientul din Ec. 5 coincide cu o estimare numerică (diferențe finite) pentru toate cele 15 ponderi.
- Pierderea nu crește la nicio iterație; pe 20.000 de meciuri simulate, antrenarea a convers în 44 de iterații și a regăsit ponderile reale cu o eroare sub 0,1.
- Cu o singură caracteristică, softmax poate face egalul cel mai probabil între două extreme.
- O clasă fără exemple de antrenare este refuzată cu o eroare.
- Caracteristici calculate de mână: pentru A acasă contra C, diferențele sunt 0 (puncte), −1 (golaveraj), −0,5 (formă) și +2 (șuturi pe poartă); pentru o echipă nouă, valorile ei sunt mediile ligii, de exemplu 1,75 puncte pe meci acasă.
- Fiecare săptămână este antrenată doar pe meciurile dinaintea zilei de luni; schimbarea rezultatului unui meci nu modifică nicio caracteristică sau predicție din ziua lui sau dinainte.

## 12. Rolul în PitchSense

- Este al treilea algoritm de predicție: probabilitățile lui vor fi comparate cu cele ale ratingului Elo și ale modelului Poisson (fazele 8–10).
- Arată cum se pot combina mai mulți indicatori într-un singur model și cât contează fiecare.
- Ponderile, istoricul pierderii și numărul de iterații pot fi afișate în interfață pentru a explica modelul.

Exemplu pentru un meci din sezonul 2025/26 (Real Madrid – Barcelona, 26 octombrie 2025), cu modelul antrenat pe cele 7.308 meciuri anterioare săptămânii: caracteristici (Elo +17,1; puncte +0,32; golaveraj −0,21; formă 0,0; șuturi pe poartă +2,05); probabilități 44,3% / 26,5% / 29,3%. Scorul real a fost 2–1. Exemplul ilustrează forma predicției; evaluarea modelului se face în fazele 8–10.

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
