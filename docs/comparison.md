# Compararea algoritmilor

Acest document compară cei patru algoritmi din PitchSense pe aceleași date. Răspunde la întrebările: ce oferă fiecare algoritm, care diferențe dintre modele sunt reale, unde funcționează bine fiecare model și cât de diferite sunt predicțiile lor. Analiza este făcută de `app/evaluation/comparison.py`, pornind de la jurnalul predicțiilor (`docs/architecture.md`, secțiunea 8). Măsurile sunt definite în `docs/evaluation.md`.

## 1. Ce oferă fiecare algoritm

| Algoritm | Ce produce | La ce folosește în PitchSense |
|---|---|---|
| Ratingul Elo | un rating pentru fiecare echipă, actualizat după fiecare meci; scorul așteptat $E$; prin modelul egalurilor, probabilitățile victorie gazde / egal / victorie oaspeți | predicții; evoluția forței echipelor în timp |
| Modelul Poisson | golurile așteptate ale fiecărei echipe; probabilitatea fiecărui scor; scorurile cele mai probabile; probabilitățile celor trei rezultate | singurul model care prezice scorul și numărul de goluri |
| Regresia logistică | probabilitățile celor trei rezultate și ponderea fiecăruia dintre cei 5 indicatori | predicții; arată cât contează fiecare indicator |
| K-Means | grupuri de echipe cu profiluri asemănătoare și profilul mediu al fiecărui grup | nu prezice meciuri: descrie tipurile de echipe și împarte evaluarea pe tipuri de meciuri |

## 2. Metoda: comparare meci cu meci

Toate modelele au predicții pentru exact aceleași 6.080 de meciuri (2010/11–2025/26). Pentru două modele A și B și o măsură (de exemplu scorul Brier), se calculează diferența pe fiecare meci, $d_i = \text{scor}_A(i) - \text{scor}_B(i)$. Media diferențelor are eroarea standard $s_d / \sqrt{n}$, iar intervalul de încredere de 95% este media ± 1,96 erori standard.

Pentru că ambele modele sunt evaluate pe aceleași meciuri, dificultatea comună a fiecărui meci se anulează. Comparația este astfel mult mai precisă decât alăturarea a două medii separate. O diferență este considerată reală doar dacă intervalul ei nu conține 0.

## 3. Care diferențe sunt reale

Rulare din 2026-10-04. La scorul Brier și la pierderea logaritmică, o diferență negativă înseamnă că primul model este mai bun; la acuratețe, una pozitivă.

| Comparație | Scor Brier | Pierdere logaritmică | Acuratețe | Concluzie |
|---|---|---|---|---|
| Elo – regresie logistică | −0,0001 [−0,0023; +0,0022] | +0,0014 [−0,0024; +0,0052] | −0,20 pp [−0,71; +0,32] | nicio diferență reală |
| Elo – Poisson | −0,0073 [−0,0108; −0,0039] | −0,0092 [−0,0148; −0,0035] | +0,56 pp [−0,10; +1,22] | Elo mai bun la probabilități |
| Poisson – regresie logistică | +0,0073 [+0,0048; +0,0097] | +0,0106 [+0,0068; +0,0143] | −0,76 pp [−1,39; −0,13] | regresia logistică mai bună la toate trei |
| Elo – frecvențele trecute | −0,0629 [−0,0703; −0,0555] | −0,0878 [−0,0991; −0,0766] | +6,74 pp [+5,65; +7,83] | Elo mult mai bun |
| Poisson – frecvențele trecute | −0,0556 [−0,0609; −0,0503] | −0,0787 [−0,0862; −0,0712] | +6,18 pp [+5,20; +7,17] | Poisson mult mai bun |
| Regresie logistică – frecvențele trecute | −0,0629 [−0,0690; −0,0567] | −0,0892 [−0,0982; −0,0803] | +6,94 pp [+5,88; +8,01] | regresia logistică mult mai bună |

(pp = puncte procentuale)

Ordinea este deci: **Elo ≈ regresia logistică > Poisson > frecvențele trecute.**

## 4. Unde funcționează bine fiecare model

În fiecare subset de meciuri, cel mai bun model este cel cu cel mai mic scor Brier. Avantajul lui față de al doilea este testat meci cu meci în interiorul subsetului.

### 4.1. Pe sezoane

| Sezon | Elo | Poisson | Regresie logistică | Frecvențele trecute | Cel mai bun |
|---|---|---|---|---|---|
| 2010/11 | 0,5506 | 0,5647 | 0,5545 | 0,6160 | Elo |
| 2011/12 | 0,5727 | 0,5772 | 0,5720 | 0,6305 | regresie logistică |
| 2012/13 | 0,5620 | 0,5679 | 0,5648 | 0,6272 | Elo |
| 2013/14 | 0,5734 | 0,5804 | 0,5734 | 0,6378 | Elo |
| 2014/15 | 0,5477 | 0,5586 | 0,5541 | 0,6457 | Elo |
| 2015/16 | 0,5713 | 0,5720 | 0,5683 | 0,6339 | regresie logistică |
| 2016/17 | 0,5414 | 0,5508 | 0,5439 | 0,6355 | Elo |
| 2017/18 | 0,5866 | 0,5925 | 0,5791 | 0,6376 | regresie logistică |
| 2018/19 | 0,6144 | 0,6132 | 0,6143 | 0,6534 | Poisson |
| 2019/20 | 0,6022 | 0,6125 | 0,6017 | 0,6449 | regresie logistică |
| 2020/21 | 0,5973 | 0,6093 | 0,5969 | 0,6602 | regresie logistică |
| 2021/22 | 0,6039 | 0,6045 | 0,5982 | 0,6534 | regresie logistică |
| 2022/23 | 0,5901 | 0,5956 | 0,5918 | 0,6373 | Elo |
| 2023/24 | 0,5732 | 0,5843 | 0,5760 | 0,6532 | Elo |
| 2024/25 | 0,5763 | 0,5902 | 0,5782 | 0,6489 | Elo |
| 2025/26 | 0,5786 | 0,5847 | 0,5753 | 0,6326 | regresie logistică |

- Elo este cel mai bun în 8 sezoane, regresia logistică în 7, Poisson într-unul. În niciun sezon avantajul nu este real: 380 de meciuri nu sunt suficiente pentru a separa modelele.
- Toate modelele sunt mai bune decât frecvențele trecute în fiecare sezon.
- Cele mai grele sezoane au fost 2018/19–2021/22 (scor Brier în jur de 0,60–0,61). Sunt sezoane cu multe egaluri (27,6–29,2%, `docs/architecture.md`, secțiunea 6.5), dar egalurile nu explică singure dificultatea: 2023/24 a avut 28,2% egaluri și a fost totuși un sezon obișnuit (0,573–0,584).
- Sezonul 2020/21, jucat fără spectatori, a fost cel mai slab sezon al frecvențelor trecute (0,6602), pentru că această referință se bazează mult pe avantajul gazdelor, care a scăzut.

### 4.2. Pe rezultatul real

| Rezultat real | Meciuri | Elo | Poisson | Regresie logistică | Frecvențele trecute | Cel mai bun |
|---|---|---|---|---|---|---|
| Victoria gazdelor | 2.836 | 0,3477 | 0,3767 | 0,3567 | 0,4276 | Elo (avantaj real) |
| Egal | 1.522 | 0,9235 | 0,8753 | 0,8994 | 0,8586 | Poisson (avantaj real) |
| Victoria oaspeților | 1.722 | 0,6506 | 0,6711 | 0,6572 | 0,7984 | Elo (avantaj real) |

Aici apar diferențe reale. Elo este cel mai bun la meciurile cu învingător, iar Poisson la egaluri. Probabilitățile mai moderate ale modelului Poisson dau egalurilor mai multă șansă, ceea ce ajută la egaluri, dar costă la meciurile cu învingător. De aceea Poisson este mai slab în total, deși este cel mai bine calibrat (`docs/evaluation.md`).

### 4.3. Pe tipuri de meciuri (grupurile K-Means)

Tipul unui meci se stabilește din grupurile momentane ale echipelor (secțiunea 2 din `docs/algorithms/kmeans.md`; 0 = elita). Tipurile se verifică în ordine, deci fiecare meci are un singur tip.

| Tip de meci | Meciuri | Elo | Poisson | Regresie logistică | Frecvențele trecute | Cel mai bun |
|---|---|---|---|---|---|---|
| implică o echipă promovată | 1.728 | 0,5803 | 0,5903 | 0,5803 | 0,6390 | Elo |
| implică o echipă din elită | 930 | 0,4368 | 0,4489 | 0,4394 | 0,6302 | Elo |
| ambele echipe din același grup | 1.132 | 0,6221 | 0,6296 | 0,6243 | 0,6502 | Elo |
| grupuri diferite | 2.290 | 0,6107 | 0,6141 | 0,6087 | 0,6411 | regresie logistică |

Niciun avantaj nu este real. Meciurile cu o echipă din elită sunt cele mai previzibile (0,437), iar cele dintre echipe din același grup cele mai grele (0,622).

Din tabelul complet „grupul gazdelor contra grupul oaspeților” (celule cu cel puțin 100 de meciuri):

- cea mai previzibilă pereche este elita acasă contra unei echipe din grupul 2 (0 v 2, 127 de meciuri, scor Brier 0,23);
- cele mai grele sunt meciurile în care gazdele sunt o echipă promovată sau din jumătatea de jos, iar oaspeții sunt din grupul 1 (scorul Brier al lui Elo: promoted v 1 0,6683; 3 v 1 0,6644; 2 v 1 0,6625);
- între echipe din jumătatea de jos (2 v 2, 3 v 2), modelele sunt abia mai bune decât frecvențele trecute (de exemplu 0,648 față de 0,652 la 2 v 2).

## 5. Cât de diferite sunt predicțiile

Distanța dintre două predicții este distanța de variație totală, $\tfrac{1}{2} \sum_c \lvert p_c - q_c \rvert$: partea din probabilitate care trebuie mutată pentru a transforma o predicție în cealaltă (0 = identice, 1 = opuse).

| Pereche | Același rezultat prezis | Distanța medie |
|---|---|---|
| Elo – regresie logistică | 93,9% | 0,0520 |
| Poisson – regresie logistică | 91,4% | 0,0569 |
| Elo – Poisson | 90,5% | 0,0808 |

Toate trei modelele prezic același rezultat în 87,9% dintre meciuri. Elo și regresia logistică sunt cele mai apropiate, ceea ce era de așteptat: regresia logistică folosește diferența Elo ca intrare.

Cele mai mari diferențe dintre modele (victorie gazde / egal / victorie oaspeți):

| Meci | Elo | Poisson | Regresie logistică |
|---|---|---|---|
| Real Madrid 0–1 Cádiz (17.10.2020) | 0,86 / 0,08 / 0,06 | 0,54 / 0,25 / 0,20 | 0,66 / 0,19 / 0,15 |
| Villarreal 2–0 Oviedo (15.08.2025) | 0,78 / 0,15 / 0,06 | 0,48 / 0,23 / 0,29 | 0,65 / 0,21 / 0,14 |
| Las Palmas 0–3 Atlético Madrid (17.01.2016) | 0,13 / 0,18 / 0,69 | 0,31 / 0,31 / 0,39 | 0,17 / 0,26 / 0,57 |
| Athletic 0–1 Cádiz (01.10.2020) | 0,63 / 0,22 / 0,15 | 0,43 / 0,29 / 0,29 | 0,33 / 0,25 / 0,42 |
| Getafe 2–0 Oviedo (13.09.2025) | 0,61 / 0,22 / 0,17 | 0,37 / 0,29 / 0,34 | 0,67 / 0,20 / 0,14 |

Toate cele cinci meciuri implică o echipă nou promovată (Cádiz în 2020/21, Oviedo în 2025/26, Las Palmas în 2015/16). Cauza este felul diferit în care modelele tratează echipele fără istoric. Elo le dă media ratingurilor echipelor retrogradate, deci le consideră slabe. Poisson le consideră echipe medii (forța 1). Regresia logistică folosește media ligii pentru indicatorii lipsă. Ca exemplu, în Real Madrid – Cádiz, Elo dădea 86% pentru Real Madrid, Poisson doar 54%; Cádiz a câștigat cu 1–0.

## 6. Concluzii

- **Ratingul Elo** este cel mai simplu model (doi parametri) și este cel mai bun sau la egalitate cu cel mai bun pe toate măsurile. Este cel mai bun la meciurile cu învingător. Este ușor prea sigur pe favoriți și, ca toate modelele, nu prezice niciodată egalul ca rezultat cel mai probabil.
- **Modelul Poisson** este singurul care prezice scorul și golurile și este cel mai bine calibrat. Este cel mai bun la egaluri, dar mai puțin precis în total decât Elo și regresia logistică, iar diferența este reală. Tratează echipele promovate ca medii, de unde vin cele mai mari diferențe față de celelalte modele.
- **Regresia logistică** este la egalitate cu Elo pe toate măsurile. Cei patru indicatori adăugați peste diferența Elo nu aduc o îmbunătățire măsurabilă. În schimb, ponderile ei arată cât contează fiecare indicator (`docs/algorithms/logistic_regression.md`).
- **K-Means** nu prezice meciuri, dar explică unde predicția este ușoară (meciurile cu elita) și unde este grea (echipe din același grup, jumătatea de jos a clasamentului).
- Toate cele trei modele de predicție sunt clar și real mai bune decât referințele, cu aproximativ 6–7 puncte procentuale de acuratețe și 0,06 la scorul Brier.

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
python -m app.evaluation.comparison
```
