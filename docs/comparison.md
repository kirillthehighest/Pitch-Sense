# Compararea algoritmilor

Acest document compară cei patru algoritmi din PitchSense pe aceleași date ale La Liga; comparația pe toate cele cinci ligi este în `docs/leagues.md`. Răspunde la întrebările: ce oferă fiecare algoritm, care diferențe dintre modele sunt reale, unde funcționează bine fiecare model și cât de diferite sunt predicțiile lor. Analiza este făcută de `app/evaluation/comparison.py`, pornind de la jurnalul predicțiilor (`docs/architecture.md`, secțiunea 8). Măsurile sunt definite în `docs/evaluation.md`.

## 1. Ce oferă fiecare algoritm

| Algoritm | Ce produce | La ce folosește în PitchSense |
|---|---|---|
| Ratingul Elo | un rating pentru fiecare echipă, actualizat după fiecare meci; scorul așteptat $E$; prin modelul egalurilor, probabilitățile victorie gazde / egal / victorie oaspeți | predicții; evoluția forței echipelor în timp |
| Modelul Poisson | golurile așteptate ale fiecărei echipe; probabilitatea fiecărui scor; scorurile cele mai probabile; probabilitățile celor trei rezultate | singurul model care prezice scorul și numărul de goluri |
| Regresia logistică | probabilitățile celor trei rezultate și ponderea fiecăruia dintre indicatori (5 până la 7, după ligă) | predicții; arată cât contează fiecare indicator |
| K-Means | grupuri de echipe cu profiluri asemănătoare și profilul mediu al fiecărui grup | nu prezice meciuri: descrie tipurile de echipe și împarte evaluarea pe tipuri de meciuri |

## 2. Metoda: comparare meci cu meci

Toate modelele au predicții pentru exact aceleași 6.080 de meciuri (2010/11–2025/26). Pentru două modele A și B și o măsură (de exemplu scorul Brier), se calculează diferența pe fiecare meci, $d_i = \text{scor}_A(i) - \text{scor}_B(i)$. Media diferențelor are eroarea standard $s_d / \sqrt{n}$, iar intervalul de încredere de 95% este media ± 1,96 erori standard.

Pentru că ambele modele sunt evaluate pe aceleași meciuri, dificultatea comună a fiecărui meci se anulează. Comparația este astfel mult mai precisă decât alăturarea a două medii separate. O diferență este considerată reală doar dacă intervalul ei nu conține 0.

## 3. Care diferențe sunt reale

Rulare din 2026-10-16, cu setările din Faza 23 (`docs/evaluation.md`, secțiunea 3). La scorul Brier și la pierderea logaritmică, o diferență negativă înseamnă că primul model este mai bun; la acuratețe, una pozitivă.

| Comparație | Scor Brier | Pierdere logaritmică | Acuratețe | Concluzie |
|---|---|---|---|---|
| Elo – regresie logistică | +0,0021 [−0,0003; +0,0045] | +0,0066 [+0,0019; +0,0113] | −0,20 pp [−0,72; +0,33] | regresia logistică mai bună doar la pierderea logaritmică |
| Elo – Poisson | −0,0035 [−0,0071; +0,0001] | −0,0014 [−0,0078; +0,0050] | +0,38 pp [−0,26; +1,02] | nicio diferență reală |
| Poisson – regresie logistică | +0,0057 [+0,0036; +0,0077] | +0,0080 [+0,0048; +0,0111] | −0,58 pp [−1,09; −0,06] | regresia logistică mai bună la toate trei |
| Elo – frecvențele trecute | −0,0622 [−0,0702; −0,0542] | −0,0848 [−0,0974; −0,0721] | +6,92 pp [+5,81; +8,04] | Elo mult mai bun |
| Poisson – frecvențele trecute | −0,0586 [−0,0643; −0,0530] | −0,0834 [−0,0914; −0,0753] | +6,55 pp [+5,53; +7,56] | Poisson mult mai bun |
| Regresie logistică – frecvențele trecute | −0,0643 [−0,0709; −0,0577] | −0,0914 [−0,1009; −0,0819] | +7,12 pp [+6,07; +8,18] | regresia logistică mult mai bună |

(pp = puncte procentuale)

Ordinea este deci: **regresia logistică ≥ Elo ≈ Poisson > frecvențele trecute**, cu regresia logistică real mai bună decât Poisson pe toate măsurile și decât Elo doar la pierderea logaritmică. Înainte de Faza 23 (rulare din 2026-10-05), ordinea era Elo ≈ regresia logistică > Poisson: Elo era real mai bun decât Poisson (−0,0051 la scorul Brier), iar regresia logistică nu se deosebea de Elo la nicio măsură. Poisson s-a apropiat de Elo (ponderile meciurilor recente și corecția Dixon–Coles), iar regresia logistică s-a îndepărtat puțin de el (cele două caracteristici în plus). Toate trei modelele rămân în urma caselor de pariuri (`docs/evaluation.md`, secțiunea 3.4).

## 4. Unde funcționează bine fiecare model

În fiecare subset de meciuri, cel mai bun model este cel cu cel mai mic scor Brier. Avantajul lui față de al doilea este testat meci cu meci în interiorul subsetului.

### 4.1. Pe sezoane

| Sezon | Elo | Poisson | Regresie logistică | Frecvențele trecute | Cel mai bun |
|---|---|---|---|---|---|
| 2010/11 | 0,5506 | 0,5630 | 0,5530 | 0,6160 | Elo |
| 2011/12 | 0,5722 | 0,5748 | 0,5710 | 0,6305 | regresie logistică |
| 2012/13 | 0,5608 | 0,5679 | 0,5624 | 0,6272 | Elo |
| 2013/14 | 0,5755 | 0,5786 | 0,5730 | 0,6378 | regresie logistică |
| 2014/15 | 0,5431 | 0,5538 | 0,5486 | 0,6457 | Elo |
| 2015/16 | 0,5752 | 0,5710 | 0,5675 | 0,6339 | regresie logistică |
| 2016/17 | 0,5383 | 0,5473 | 0,5413 | 0,6355 | Elo |
| 2017/18 | 0,5924 | 0,5863 | 0,5813 | 0,6376 | regresie logistică |
| 2018/19 | 0,6200 | 0,6126 | 0,6132 | 0,6534 | Poisson |
| 2019/20 | 0,6027 | 0,6078 | 0,6014 | 0,6449 | regresie logistică |
| 2020/21 | 0,5981 | 0,6017 | 0,5942 | 0,6602 | regresie logistică |
| 2021/22 | 0,6017 | 0,6018 | 0,5989 | 0,6534 | regresie logistică |
| 2022/23 | 0,5912 | 0,5949 | 0,5894 | 0,6373 | regresie logistică |
| 2023/24 | 0,5737 | 0,5824 | 0,5743 | 0,6532 | Elo |
| 2024/25 | 0,5781 | 0,5858 | 0,5768 | 0,6489 | regresie logistică |
| 2025/26 | 0,5800 | 0,5803 | 0,5731 | 0,6326 | regresie logistică |

- Regresia logistică este cea mai bună în 10 sezoane, Elo în 5, Poisson în unul. În niciun sezon avantajul nu este real: 380 de meciuri nu sunt suficiente pentru a separa modelele.
- Toate modelele sunt mai bune decât frecvențele trecute în fiecare sezon.
- Cele mai grele sezoane au fost 2018/19–2021/22 (scor Brier în jur de 0,59–0,62). Sunt sezoane cu multe egaluri (27,6–29,2%, `docs/architecture.md`, secțiunea 6.5), dar egalurile nu explică singure dificultatea: 2023/24 a avut 28,2% egaluri și a fost totuși un sezon obișnuit (0,574–0,582).
- Sezonul 2020/21, jucat fără spectatori, a fost cel mai slab sezon al frecvențelor trecute (0,6602), pentru că această referință se bazează mult pe avantajul gazdelor, care a scăzut.

### 4.2. Pe rezultatul real

| Rezultat real | Meciuri | Elo | Poisson | Regresie logistică | Frecvențele trecute | Cel mai bun |
|---|---|---|---|---|---|---|
| Victoria gazdelor | 2.836 | 0,3507 | 0,3810 | 0,3538 | 0,4276 | Elo |
| Egal | 1.522 | 0,9334 | 0,8579 | 0,9068 | 0,8586 | Poisson (avantaj real) |
| Victoria oaspeților | 1.722 | 0,6395 | 0,6687 | 0,6502 | 0,7984 | Elo (avantaj real) |

Aici apar diferențe reale. Elo este cel mai bun la meciurile cu învingător (real la victoriile oaspeților), iar Poisson la egaluri, unde, cu corecția Dixon–Coles, ajunge chiar puțin înaintea frecvențelor trecute. Probabilitățile mai moderate ale modelului Poisson dau egalurilor mai multă șansă, ceea ce ajută la egaluri, dar costă la meciurile cu învingător. Elo face invers: e sigur pe favoriți, câștigă când aceștia câștigă și pierde mult la egaluri.

### 4.3. Pe tipuri de meciuri (grupurile K-Means)

Tipul unui meci se stabilește din grupurile momentane ale echipelor (secțiunea 2 din `docs/algorithms/kmeans.md`; 0 = elita). Tipurile se verifică în ordine, deci fiecare meci are un singur tip.

| Tip de meci | Meciuri | Elo | Poisson | Regresie logistică | Frecvențele trecute | Cel mai bun |
|---|---|---|---|---|---|---|
| implică o echipă promovată | 1.728 | 0,5816 | 0,5879 | 0,5797 | 0,6390 | regresie logistică |
| implică o echipă din elită | 930 | 0,4387 | 0,4439 | 0,4343 | 0,6302 | regresie logistică |
| ambele echipe din același grup | 1.132 | 0,6206 | 0,6260 | 0,6229 | 0,6502 | Elo |
| grupuri diferite | 2.290 | 0,6117 | 0,6115 | 0,6081 | 0,6411 | regresie logistică (avantaj real) |

Un singur avantaj este real: regresia logistică la meciurile dintre echipe din grupuri diferite. Meciurile cu o echipă din elită sunt cele mai previzibile (0,434), iar cele dintre echipe din același grup cele mai grele (0,621).

Din tabelul complet „grupul gazdelor contra grupul oaspeților” (celule cu cel puțin 100 de meciuri):

- cea mai previzibilă pereche este elita acasă contra unei echipe din grupul 2 (0 v 2, 127 de meciuri, scor Brier 0,22);
- cele mai grele sunt meciurile în care gazdele sunt o echipă promovată sau din jumătatea de jos, iar oaspeții sunt din grupul 1 (scorul Brier al lui Elo: promoted v 1 0,6670; 3 v 1 0,6662; 2 v 1 0,6618);
- între echipe din jumătatea de jos (2 v 2, 3 v 2), modelele sunt abia mai bune decât frecvențele trecute (de exemplu 0,646–0,649 față de 0,652 la 2 v 2).

## 5. Cât de diferite sunt predicțiile

Distanța dintre două predicții este distanța de variație totală, $\tfrac{1}{2} \sum_c \lvert p_c - q_c \rvert$: partea din probabilitate care trebuie mutată pentru a transforma o predicție în cealaltă (0 = identice, 1 = opuse).

| Pereche | Același rezultat prezis | Distanța medie |
|---|---|---|
| Poisson – regresie logistică | 94,3% | 0,0486 |
| Elo – regresie logistică | 93,6% | 0,0556 |
| Elo – Poisson | 90,9% | 0,0841 |

Toate trei modelele prezic același rezultat în 89,4% dintre meciuri. Din Faza 23, în La Liga, regresia logistică primește golurile așteptate ale modelului Poisson, așa că s-a apropiat de el (înainte, Poisson – regresie logistică: 88,9% și 0,0616); Elo și regresia logistică rămân apropiate, pentru că diferența Elo este tot o intrare. Elo și Poisson s-au îndepărtat (înainte 90,0% și 0,0733): Elo a devenit mai sigur pe favoriți, iar Poisson mai prudent.

Cele mai mari diferențe dintre modele (victorie gazde / egal / victorie oaspeți):

| Meci | Elo | Poisson | Regresie logistică |
|---|---|---|---|
| Atlético Madrid 4–0 Cádiz (07.11.2020) | 0,80 / 0,17 / 0,03 | 0,45 / 0,32 / 0,23 | 0,54 / 0,20 / 0,26 |
| Real Madrid 0–1 Cádiz (17.10.2020) | 0,88 / 0,08 / 0,04 | 0,54 / 0,26 / 0,20 | 0,69 / 0,15 / 0,15 |
| Girona 0–1 Sevilla (17.09.2017) | 0,17 / 0,23 / 0,59 | 0,46 / 0,25 / 0,29 | 0,38 / 0,25 / 0,37 |
| Oviedo 0–3 Real Madrid (24.08.2025) | 0,03 / 0,18 / 0,78 | 0,26 / 0,25 / 0,49 | 0,17 / 0,22 / 0,62 |
| Las Palmas 0–3 Atlético Madrid (17.01.2016) | 0,10 / 0,19 / 0,70 | 0,26 / 0,32 / 0,41 | 0,20 / 0,22 / 0,57 |

Toate cele cinci meciuri implică o echipă nou promovată (Cádiz în 2020/21, Girona în 2017/18, Oviedo în 2025/26, Las Palmas în 2015/16). Cauza este felul diferit în care modelele tratează echipele fără istoric. Elo le dă media ratingurilor echipelor retrogradate, deci le consideră slabe. Poisson le consideră echipe medii (forța 1). Regresia logistică folosește media ligii pentru indicatorii lipsă. Ca exemplu, în Atlético Madrid – Cádiz (07.11.2020), Elo dădea 80% pentru Atlético, Poisson și regresia logistică doar 45% și 54%; Atlético a câștigat cu 4–0. În Real Madrid – Cádiz, trei săptămâni mai devreme, Elo dădea 88% pentru Real Madrid, iar Cádiz a câștigat.

## 6. Concluzii

- **Ratingul Elo** este cel mai simplu model (trei alegeri: $K$, $H$ și ponderea golurilor) și este cel mai bun la meciurile cu învingător. În La Liga nu se deosebește real de regresia logistică la scorul Brier și la acuratețe, dar pierde la pierderea logaritmică, pentru că este prea sigur pe favoriți (eroarea de calibrare 0,0252, cea mai mare dintre modele).
- **Modelul Poisson** este singurul care prezice scorul și golurile. Este cel mai bun la egaluri, iar din Faza 23 nu se mai deosebește real de Elo; regresia logistică rămâne real mai bună decât el pe toate măsurile. Tratează echipele promovate ca medii, de unde vin cele mai mari diferențe față de celelalte modele.
- **Regresia logistică** are cele mai bune valori pe toate cele trei măsuri și este cea mai bine calibrată dintre modele. Avantajul ei față de Elo este real în La Liga doar la pierderea logaritmică, dar în Premier League și Serie A, și pe toate cele cinci ligi la un loc, este real și la scorul Brier (`docs/leagues.md`). Ponderile ei arată cât contează fiecare indicator (`docs/algorithms/logistic_regression.md`).
- **K-Means** nu prezice meciuri, dar explică unde predicția este ușoară (meciurile cu elita) și unde este grea (echipe din același grup, jumătatea de jos a clasamentului).
- Toate cele trei modele de predicție sunt clar și real mai bune decât referințele, cu aproximativ 6,5–7 puncte procentuale de acuratețe și 0,06 la scorul Brier, dar toate rămân în urma caselor de pariuri, cu 0,010–0,016 la scorul Brier (`docs/evaluation.md`, secțiunea 3.4).

## 7. Limitări ale comparației

- O singură ligă și 16 sezoane: concluziile pot fi diferite în alte competiții.
- În subseturile mici (un sezon, o pereche de grupuri), diferențele dintre modele nu pot fi separate de zgomot.
- Intervalele de încredere folosesc aproximarea normală, potrivită pentru mii de meciuri, dar mai puțin sigură pentru subseturi mici.
- Mai multe comparații simultane cresc șansa ca o diferență să pară reală întâmplător; diferențele principale (secțiunea 3) au însă intervale departe de 0.
- Tipurile de meciuri depind de grupurile K-Means, care se schimbă de la un sezon la altul (`docs/algorithms/kmeans.md`).

## 8. Reproducere

```bash
python -m app.data.build_database
python -m app.evaluation.backtesting
python -m app.evaluation.comparison SP1
```
