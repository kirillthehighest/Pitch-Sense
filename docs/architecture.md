# Arhitectura aplicației PitchSense

Acest document descrie structura aplicației, fluxul datelor și deciziile tehnice luate până acum (fazele 0–7). Se actualizează ori de câte ori structura se schimbă.

## 1. Principii

- **Algoritmii sunt nucleul proiectului.** Cei patru algoritmi (ratingul Elo, modelul Poisson, regresia logistică, K-Means) sunt implementați de noi, pornind de la formulele matematice. Nu folosim implementări gata făcute (scikit-learn, SciPy, statsmodels sau pachete de predicție pentru fotbal).
- **Straturile sunt separate.** Datele, statisticile, algoritmii, evaluarea și interfața nu se amestecă. Interfața nu conține logică de calcul.
- **Fără scurgere de informații (data leakage).** Predicția pentru un meci folosește doar informații disponibile înainte de acel meci.
- **Evaluarea este cronologică (walk-forward).** Nu folosim împărțirea aleatorie a datelor ca metodă principală de evaluare.

## 2. Straturi

| Pachet | Responsabilitate | Dependențe principale |
|---|---|---|
| `app/algorithms` | Implementarea celor patru algoritmi. Doar matematică, fără citire sau scriere de fișiere. | biblioteca standard Python, NumPy |
| `app/data` | Modelele de date, citirea fișierelor CSV, validarea și normalizarea datelor, stocarea în SQLite. | pandas, `sqlite3` |
| `app/statistics` | Statisticile echipelor și caracteristicile (features) calculate „la o anumită dată”, doar din meciurile anterioare. | `app.data`, NumPy, pandas |
| `app/prediction` | Rulează modelele pentru un meci și întoarce rezultatele într-un format comun. | `app.algorithms`, `app.statistics`, `app.data` |
| `app/evaluation` | Backtesting cronologic, metrici de evaluare, compararea modelelor. | straturile de mai sus |
| `app/visualization` | Construiește graficele din rezultate deja calculate, fără calcule proprii. | matplotlib |
| `app/ui` | Interfața grafică: preia datele de intrare, apelează serviciile și afișează rezultatele. | PySide6 și celelalte straturi |

## 3. Reguli verificate automat

Testul `tests/test_architecture.py` verifică la fiecare rulare că:

- `app/algorithms` importă doar biblioteca standard și NumPy, nimic din restul aplicației;
- doar `app/ui` importă PySide6;
- matplotlib este importat doar în `app/visualization` și `app/ui`;
- nicio parte a aplicației nu importă scikit-learn, SciPy sau statsmodels.

## 4. Fluxul datelor

```
data/raw/SP1/*.csv            fișierele originale, nemodificate
        │
        ▼
app/data                      validare, normalizare → baza de date SQLite
        │
        ▼
app/statistics                statistici „la o anumită dată” (doar meciuri anterioare)
        │
        ▼
app/prediction  ◄──────────── app/algorithms (Elo, Poisson, regresie logistică, K-Means)
        │
        ▼
app/evaluation                backtesting cronologic, metrici, comparație
        │
        ▼
app/visualization → app/ui    grafice și interfața grafică
```

## 5. Stratul de date (Faza 1)

### 5.1. Module

| Modul | Rol |
|---|---|
| `models.py` | Înregistrările `Match`, `MatchStatistics` și rezultatul `Outcome` (H, D, A). Un `Match` nu poate fi modificat după creare și refuză datele imposibile. |
| `preprocessing.py` | Validează rândurile brute și le transformă în înregistrări `Match`; verifică structura unui sezon; definește ordinea cronologică. |
| `loader.py` | Citește un fișier de sezon sau toate sezoanele unei competiții. |
| `repository.py` | Stochează și interoghează meciurile în SQLite. |
| `build_database.py` | Comanda care reconstruiește baza de date din fișierele brute. |
| `paths.py` | Locul unic în care sunt definite căile către fișierele de date. |

### 5.2. Înregistrarea unui meci (`Match`)

| Câmp | Tip | Descriere |
|---|---|---|
| `competition` | text | codul competiției, de exemplu `SP1` pentru La Liga |
| `season` | text | sezonul, de forma `2006-07`, luat din numele fișierului |
| `match_date` | dată | ziua meciului |
| `kickoff_time` | oră sau lipsă | ora de începere; există doar din sezonul 2019-20 |
| `home_team`, `away_team` | text | echipa gazdă și echipa oaspete |
| `home_goals`, `away_goals` | întreg ≥ 0 | golurile la finalul meciului |
| `result` | `H` / `D` / `A` | victoria gazdelor, egal, victoria oaspeților |
| `statistics` | `MatchStatistics` sau lipsă | cele 12 statistici ale meciului: șuturi, șuturi pe poartă, faulturi, cornere, cartonașe galbene și roșii, pentru fiecare echipă |

Statisticile descriu meciul însuși, deci nu sunt cunoscute înainte de începerea lui. Ele pot fi folosite doar pentru meciurile care urmează.

### 5.3. Reguli de validare

La citirea unui fișier:

- coloanele obligatorii (`Div`, `Date`, `HomeTeam`, `AwayTeam`, `FTHG`, `FTAG`, `FTR`) trebuie să existe; toate coloanele sunt citite după nume, nu după poziție;
- golurile și statisticile sunt numere întregi nenegative;
- rezultatul este `H`, `D` sau `A` și corespunde scorului;
- numele echipelor nu lipsesc, iar o echipă nu poate juca cu ea însăși;
- data meciului se încadrează în sezon, între 1 iulie și 31 iulie a anului următor (sezonul 2019/20 s-a încheiat abia pe 19 iulie 2020);
- nu există meciuri duplicate, iar toate rândurile unui fișier aparțin aceleiași competiții;
- toate problemele dintr-un fișier sunt raportate împreună, fiecare cu numărul liniei.

La construirea bazei de date, fiecare sezon trebuie să fie un campionat complet în sistem tur-retur: 20 de echipe, 380 de meciuri, 38 de meciuri pe echipă, iar fiecare echipă găzduiește fiecare adversar o singură dată.

### 5.4. Particularități ale fișierelor sursă

- Datele sunt scrise `zz/ll/aa` până în sezonul 2017-18 și `zz/ll/aaaa` începând cu 2018-19.
- Fișierele 2024-25 și 2025-26 încep cu un marcaj BOM; ele sunt citite cu codificarea `utf-8-sig`.
- Numărul de coloane variază între 61 și 131, deoarece coloanele cu cotele caselor de pariuri se schimbă. De aceea coloanele sunt alese după nume.
- Ora de începere apare doar din sezonul 2019-20.
- Rândurile complet goale sunt ignorate.

### 5.5. Structura bazei de date

Baza de date `data/pitchsense.db` are un singur tabel, `matches`:

| Coloană | Tip SQLite | Observații |
|---|---|---|
| `id` | INTEGER | cheie primară |
| `competition`, `season` | TEXT | obligatorii |
| `match_date` | TEXT | obligatoriu, format ISO 8601 (`AAAA-LL-ZZ`) |
| `kickoff_time` | TEXT | `HH:MM` sau NULL |
| `home_team`, `away_team` | TEXT | obligatorii |
| `home_goals`, `away_goals` | INTEGER | obligatorii, cel puțin 0 |
| `result` | TEXT | obligatoriu: `H`, `D` sau `A` |
| `home_shots` … `away_red_cards` | INTEGER | cele 12 statistici; NULL când sursa nu le are |

Constrângeri: un meci este unic după competiție, dată și echipe (`UNIQUE (competition, match_date, home_team, away_team)`). Un index pe `(competition, season)` accelerează interogările pe sezon.

### 5.6. Construirea bazei de date

```bash
python -m app.data.build_database
```

Comanda parcurge fiecare folder din `data/raw/` (numele folderului este codul competiției), validează toate sezoanele și verifică dacă sunt complete. Scrie mai întâi într-un fișier temporar și înlocuiește `data/pitchsense.db` doar dacă totul a reușit. Baza de date nu este inclusă în git: se reconstruiește oricând din fișierele brute, care rămân singura sursă de adevăr.

Rezultat la 2026-10-04: 7.600 de meciuri în 20 de sezoane, toate complete. Meciurile citite din baza de date sunt identice cu cele încărcate direct din fișierele CSV.

## 6. Statisticile echipelor (Faza 2)

Modulul `app/statistics/team_statistics.py` calculează statisticile unei echipe și ale ligii „la o anumită dată”, adică doar din meciurile jucate **strict înaintea** acelei zile. Meciul pentru care se face predicția și toate celelalte meciuri din aceeași zi sunt excluse. Motivul: sezoanele vechi nu au ora de începere, deci nu se poate ști care meciuri din aceeași zi s-au încheiat înainte.

### 6.1. Ce oferă

| Funcție | Rezultat |
|---|---|
| `MatchHistory` | meciurile unei singure competiții, indexate cronologic pe echipe; toate interogările trec prin ea |
| `team_statistics` | meciuri jucate, victorii, egaluri, înfrângeri, goluri marcate și primite, puncte, golaveraj, puncte pe meci, procentul de victorii, goluri pe meci |
| `team_match_statistics` | media pe meci a șuturilor, șuturilor pe poartă, faulturilor, cornerelor și cartonașelor galbene și roșii, atât ale echipei, cât și ale adversarilor |
| `recent_form` | ultimele N rezultate ale echipei (implicit 5), de la cel mai vechi la cel mai recent: `W` (victorie), `D` (egal), `L` (înfrângere) |
| `league_averages` | media golurilor gazdelor și ale oaspeților pe meci și frecvența rezultatelor `H`, `D`, `A` în întreaga ligă |

### 6.2. Selecții

Fiecare interogare poate restrânge meciurile luate în calcul:

- **locul** (doar pentru echipe): toate meciurile, doar cele de acasă sau doar cele din deplasare;
- **sezonul**: doar meciurile sezonului dat („sezonul până acum”);
- **ultimele N**: doar cele mai recente N meciuri rămase, chiar dacă unele sunt din sezonul anterior.

Filtrele se aplică în această ordine: locul, sezonul, ultimele N. De exemplu, „ultimele 5 meciuri acasă” înseamnă ultimele 5 dintre meciurile jucate acasă.

Când selecția nu conține niciun meci (de exemplu, pentru o echipă nou promovată, înaintea primului ei meci), valorile medii sunt „fără date” (`None`), nu 0. Fiecare model decide, în faza lui, cum tratează această situație. Mediile statisticilor de meci folosesc doar meciurile care au statistici înregistrate.

### 6.3. Algoritmul de selecție și complexitatea

Pentru fiecare echipă se păstrează lista meciurilor ei în ordine cronologică și lista datelor acestor meciuri; pentru ligă, la fel, lista tuturor meciurilor. O selecție are doi pași:

1. o căutare binară găsește poziția primului meci cu data mai mare sau egală cu ziua D; toate meciurile dinaintea acestei poziții sunt strict anterioare zilei D;
2. lista este parcursă înapoi de la această poziție, iar meciurile care trec filtrele sunt păstrate; parcurgerea se oprește imediat ce selecția este completă.

```
SELECTEAZĂ_ÎNAINTE(meciuri, date, D, sezon, ultimele, păstrează):
    c ← CĂUTARE_BINARĂ_STÂNGA(date, D)        ▷ primul meci cu data ≥ D
    rezultat ← listă vidă
    pentru i ← c − 1 descrescător până la 0:
        m ← meciuri[i]
        dacă sezon este dat și m.sezon ≠ sezon:
            dacă m.sezon < sezon: oprește       ▷ meciurile rămase sunt și mai vechi
            altfel: continuă
        dacă nu păstrează(m): continuă         ▷ de exemplu, filtrul acasă/deplasare
        adaugă m la rezultat
        dacă ultimele este dat și |rezultat| = ultimele: oprește
    returnează rezultat în ordine inversă      ▷ cel mai vechi meci primul
```

Notații: n — numărul total de meciuri (7.600); nₑ — numărul de meciuri ale unei echipe (cel mult 760 în 20 de sezoane); k — numărul de meciuri parcurse înapoi.

| Operație | Timp | Memorie suplimentară |
|---|---|---|
| Construirea `MatchHistory` | O(n log n) pentru sortare + O(n) pentru indexare | O(n) |
| O selecție pentru o echipă | O(log nₑ + k) | O(k) |
| O selecție pentru ligă | O(log n + k) | O(k) |
| Varianta naivă: filtrarea tuturor meciurilor la fiecare interogare | O(n) | O(k) |

În practică k este mic: cel mult 38 pentru „sezonul până acum” al unei echipe, N pentru „ultimele N” (aproximativ 2N cu filtrul acasă/deplasare) și cel mult 380 pentru sezonul ligii. Doar o selecție fără niciun filtru parcurge tot istoricul echipei (nₑ meciuri).

Pentru backtesting, unde se cer statistici înaintea fiecăruia dintre cele n meciuri, varianta indexată costă în total O(n (log n + k)), față de O(n²) pentru varianta naivă.

### 6.4. Verificare

Testele automate verifică, pentru fiecare echipă, fiecare zi și cinci tipuri de selecție, că schimbarea rezultatului și a statisticilor unui meci nu modifică nimic din ce se calculează în ziua lui sau înainte, dar se vede începând cu ziua următoare. Când regula de tăiere a fost stricată intenționat, într-o copie a codului, toate cele 12 teste care verifică limita zilei au eșuat.

Rulare pe datele reale din 2026-10-04 (La Liga, 2006/07–2025/26; Python 3.14.7, Mac cu procesor Apple Silicon):

- la finalul fiecărui sezon, toate cele 20 de echipe au 38 de meciuri, dintre care 19 acasă; suma punctelor este 3 × meciurile cu învingător + 2 × egalurile; numărul victoriilor este egal cu numărul înfrângerilor, iar golurile marcate sunt egale cu cele primite;
- clasamentele finale ale tuturor sezoanelor sunt identice cu cele calculate independent, prin parcurgerea directă a meciurilor;
- pe un eșantion aleator de 400 de meciuri, selecțiile „sezonul până acum” și „ultimele 5 meciuri” sunt identice cu cele obținute prin filtrarea directă a tuturor meciurilor, iar meciul țintă nu apare niciodată în selecție;
- totalurile coincid cu clasamentele publicate: Real Madrid 2011/12 – 100 de puncte și 121 de goluri; Barcelona 2012/13 – 100 de puncte și 115 goluri; Real Madrid și Barcelona 2006/07 – câte 76 de puncte;
- viteză: 83.600 de interogări (cinci statistici pentru fiecare echipă înaintea fiecăruia dintre cele 7.600 de meciuri, plus media ligii) au durat 0,72 s, adică aproximativ 9 µs pe interogare. Selecția „sezonul până acum” pentru ambele echipe ale tuturor meciurilor a durat 0,022 s cu index, față de 2,64 s cu varianta naivă, deci de circa 120 de ori mai puțin.

### 6.5. Mediile ligii pe sezoane

Calculate cu `league_averages` la finalul fiecărui sezon (rulare din 2026-10-04).

| Sezon | Victorii gazde | Egaluri | Victorii oaspeți | Goluri gazde / meci | Goluri oaspeți / meci |
|---|---|---|---|---|---|
| 2006/07 | 45,3% | 25,8% | 28,9% | 1,36 | 1,12 |
| 2007/08 | 47,9% | 22,9% | 29,2% | 1,55 | 1,14 |
| 2008/09 | 48,4% | 21,8% | 29,7% | 1,66 | 1,24 |
| 2009/10 | 51,1% | 25,0% | 23,9% | 1,60 | 1,11 |
| 2010/11 | 51,8% | 20,8% | 27,4% | 1,64 | 1,11 |
| 2011/12 | 49,5% | 24,7% | 25,8% | 1,68 | 1,08 |
| 2012/13 | 49,7% | 22,1% | 28,2% | 1,69 | 1,18 |
| 2013/14 | 47,1% | 22,6% | 30,3% | 1,63 | 1,12 |
| 2014/15 | 45,0% | 23,9% | 31,1% | 1,54 | 1,12 |
| 2015/16 | 48,2% | 24,2% | 27,6% | 1,62 | 1,13 |
| 2016/17 | 47,6% | 23,4% | 28,9% | 1,66 | 1,28 |
| 2017/18 | 47,1% | 22,6% | 30,3% | 1,55 | 1,15 |
| 2018/19 | 44,2% | 28,9% | 26,8% | 1,45 | 1,13 |
| 2019/20 | 45,8% | 27,6% | 26,6% | 1,44 | 1,04 |
| 2020/21 | 41,6% | 28,7% | 29,7% | 1,37 | 1,14 |
| 2021/22 | 43,4% | 29,2% | 27,4% | 1,42 | 1,08 |
| 2022/23 | 47,9% | 23,4% | 28,7% | 1,46 | 1,06 |
| 2023/24 | 43,9% | 28,2% | 27,9% | 1,48 | 1,16 |
| 2024/25 | 44,5% | 25,5% | 30,0% | 1,45 | 1,17 |
| 2025/26 | 48,9% | 24,5% | 26,6% | 1,57 | 1,12 |
| **Total** | **46,9%** | **24,8%** | **28,2%** | **1,54** | **1,13** |

Observații:

- Gazdele câștigă 46,9% dintre meciuri. Un model care prezice mereu victoria gazdelor ar avea, pe întregul set de date, o acuratețe de circa 47%; acesta este pragul minim pe care trebuie să-l depășească algoritmii.
- Sezonul 2020/21, jucat fără spectatori, are cel mai mic procent de victorii ale gazdelor (41,6%).
- Egalurile sunt mai frecvente în sezoanele 2018/19–2025/26 (27,0%) decât în 2007/08–2017/18 (23,1%). Acest lucru contează pentru modelele care trebuie să estimeze probabilitatea unui egal.

## 7. Motorul de predicție (Faza 7)

Modulul `app/prediction/prediction_engine.py` reunește cele trei modele care prezic rezultatul meciurilor: ratingul Elo, modelul Poisson și regresia logistică. K-Means nu prezice meciuri; el descrie tipuri de echipe (vezi `docs/algorithms/kmeans.md`).

### 7.1. Formatul comun al predicțiilor

Formatul este definit în `app/prediction/outputs.py`:

- `OutcomeProbabilities` conține probabilitățile victoriei gazdelor, egalului și victoriei oaspeților, mereu în această ordine. Sunt respinse valorile negative, infinite sau lipsă și sumele care diferă de 1 cu mai mult de $10^{-9}$. Rezultatul cel mai probabil (`most_likely`) se alege, la egalitate, în ordinea gazde, egal, oaspeți.
- `ModelPrediction` conține numele modelului, probabilitățile și, doar pentru modelul Poisson, golurile așteptate și tabelul scorurilor.

Fiecare predicție este verificată când este convertită în acest format, deci o predicție invalidă nu poate ajunge în evaluare.

### 7.2. Ce oferă fiecare model

| Model | Probabilitățile | Informații în plus | Când lipsește predicția |
|---|---|---|---|
| Elo | scorul așteptat $E$, transformat prin modelul egalurilor | – | săptămâna începe cu mai puțin de 100 de meciuri anterioare |
| Poisson | din tabelul scorurilor | goluri așteptate, tabelul scorurilor, scorurile cele mai probabile | liga nu are încă goluri acasă și în deplasare (prima zi a datelor) |
| Regresie logistică | softmax | – | săptămâna începe cu mai puțin de 100 de meciuri anterioare sau fără toate cele trei rezultate |

Modelul egalurilor din Elo și regresia logistică sunt reantrenate în fiecare luni, pe toate meciurile dinaintea acelei zile de luni. Regula este definită într-un singur loc, `app/prediction/schedule.py`.

### 7.3. Toate meciurile: `predict_history`

Pentru meciurile unei competiții, `predict_history` rulează cele trei modele și întoarce, pentru fiecare meci, în ordine cronologică, predicțiile disponibile. `has_all_models` arată dacă toate cele trei modele au o predicție. Aceste rezultate sunt intrarea evaluării cronologice (Faza 8).

### 7.4. Un singur meci: `predict_fixture`

`predict_fixture` primește un sezon, echipa gazdă, echipa oaspete și o dată. Ambele echipe trebuie să fi jucat în acel sezon, iar data trebuie să fie în interiorul sezonului.

- Dacă meciul s-a jucat, predicțiile sunt exact cele din `predict_history`, iar rezultatul real este întors și el, pentru comparație.
- Dacă meciul nu s-a jucat („ce-ar fi dacă”), este adăugat temporar un meci înlocuitor, cu un scor fictiv. Scorul fictiv nu poate influența predicția acestui meci, pentru că niciun model nu folosește rezultatele din ziua pe care o prezice. Testele de scurgere a informațiilor demonstrează acest lucru.
- Sunt folosite doar sezoanele până la cel cerut, pentru că sezoanele ulterioare nu pot schimba predicția.

Același cod servește evaluarea și interfața, deci cele două nu pot da rezultate diferite. Testele verifică:

- pentru fiecare meci jucat, `predict_fixture` dă exact predicția din `predict_history`;
- dacă un meci real este scos din date și cerut ca meci ipotetic, predicția este exact cea pe care a avut-o meciul real;
- sezoanele ulterioare nu schimbă predicția.

### 7.5. Verificare pe datele reale

Rulare din 2026-10-04, pe toate cele 7.600 de meciuri:

| Model | Predicții |
|---|---|
| Elo | 7.500 |
| Poisson | 7.599 |
| Regresie logistică | 7.490 |
| toate trei | 7.490 (de la 25 noiembrie 2006) |

Toate cele 1.140 de meciuri de calibrare și toate cele 6.080 de meciuri de evaluare (2010/11–2025/26) au predicții de la toate cele trei modele, deci compararea lor se poate face în condiții identice, fără a elimina niciun meci. `predict_history` rulează pe tot istoricul în aproximativ 7 s.

Exemple de predicții pentru un singur meci (victorie gazde / egal / victorie oaspeți):

| Meci | Elo | Poisson | Regresie logistică | Rezultat |
|---|---|---|---|---|
| Real Madrid – Barcelona, 26.10.2025 | 50,2% / 26,8% / 23,0% | 45,1% / 23,2% / 31,7% (goluri așteptate 1,75–1,43) | 44,3% / 26,5% / 29,3% | 2–1 |
| Barcelona – Real Madrid, 29.11.2010 | 50,8% / 25,5% / 23,6% | 49,4% / 23,2% / 27,4% (1,79–1,28) | 41,5% / 26,0% / 32,6% | 5–0 |
| Barcelona – Oviedo, 01.03.2026 (ipotetic) | 89,2% / 9,2% / 1,6% | 78,2% / 13,5% / 8,2% (2,78–0,81) | 86,1% / 10,4% / 3,5% | nejucat |

Scoaterea meciului Real Madrid – Barcelona din date și cererea lui ca meci ipotetic dau exact aceleași probabilități.

Limitare: `predict_fixture` recalculează toate modelele. Pentru sezoanele recente durează aproximativ 7 s (pentru 2010/11, aproximativ 1 s). Interfața (Faza 11) va trebui să reutilizeze rezultatele calculate o dată.

## 8. Backtesting cronologic

Meciurile sunt parcurse în ordinea datelor. Pentru fiecare zi de joc D:

1. modelele care se antrenează (regresia logistică, parametrii modelului Poisson) sunt reantrenate, după un program documentat, doar pe meciurile dinaintea zilei D;
2. fiecare model prezice toate meciurile din ziua D, iar predicțiile sunt salvate;
3. abia apoi se dezvăluie rezultatele din ziua D și se actualizează modelele cu stare (ratingurile Elo).

Metricile se calculează din jurnalul predicțiilor salvate, în aceleași condiții pentru toate modelele.

## 9. Setul de date și perioadele

Sursa datelor este Football-Data.co.uk: La Liga (`SP1`), 20 de sezoane încheiate, 2006/07–2025/26 (7.600 de meciuri).

| Perioadă | Rol |
|---|---|
| 2006/07 | Încălzire: construiește ratingurile și istoricul; nu este evaluată. |
| 2007/08–2009/10 | Calibrare: se aleg hiperparametrii; rezultatele nu sunt raportate. |
| 2010/11–2025/26 | Evaluarea raportată: 16 sezoane, 6.080 de meciuri. |

## 10. Tehnologii

| Componentă | Versiune | Rol |
|---|---|---|
| Python | 3.14 | limbajul aplicației |
| PySide6-Essentials | 6.11.2 | interfața grafică (Qt) |
| NumPy | 2.5.3 | calculele numerice din algoritmi |
| pandas | 3.0.6 | citirea și prelucrarea datelor |
| matplotlib | 3.11.2 | grafice |
| SQLite (`sqlite3`, inclus în Python) | – | stocarea datelor prelucrate |
| pytest | 9.1.1 | testare |
| ruff | 0.16.10 | verificarea și formatarea codului |

## 11. Decizii tehnice

| Decizie | Motiv |
|---|---|
| Python 3.14 | Este cea mai nouă versiune suportată de PySide6 6.11, care cere Python < 3.15. |
| `PySide6-Essentials` în locul pachetului complet `PySide6` | Conține modulele Qt de care avem nevoie (QtCore, QtGui, QtWidgets). Pachetul complet adaugă circa 330 MB de module nefolosite (web, 3D, multimedia), iar graficele sunt realizate cu matplotlib. |
| `pyproject.toml` cu versiuni fixe (`==`), mediu virtual `.venv` și `pip` | Aceleași versiuni pe macOS și Windows. Actualizările se fac intenționat și sunt urmate de rularea tuturor testelor. |
| ruff, fără verificator static de tipuri | Un singur instrument rapid pentru stil și erori frecvente. Adnotările de tip rămân obligatorii. |
| Avertismentele sunt tratate ca erori în teste | Schimbările de API din pandas 3 și NumPy 2 sunt observate imediat, nu ignorate. |
| Interfața și codul în engleză; documentația și raportul în română | Decizia echipei. |
| Statisticile unui meci sunt păstrate doar dacă există toate cele 12 valori | Un model care folosește statistici primește mereu setul complet; un meci cu date parțiale este tratat ca un meci fără statistici. |
| Cotele de pariuri și scorul la pauză nu sunt încărcate | Nu sunt folosite de niciun algoritm, iar pariurile sunt în afara scopului proiectului. |
| Numele echipelor rămân ca în sursă (`Ath Madrid`, `Sociedad`) | Sunt consecvente în toate cele 20 de sezoane; nume mai prietenoase se pot adăuga ulterior într-un singur loc. |
| Ordinea cronologică este definită într-un singur loc: data, apoi ora (necunoscută întâi), apoi echipa gazdă | Aceeași ordine în fișiere, în baza de date și, mai târziu, în backtesting. |
| Baza de date se reconstruiește integral din fișierele brute, printr-un fișier temporar | Baza de date nu poate rămâne scrisă pe jumătate, iar fișierele brute rămân singura sursă de adevăr. |
| Data și ora sunt stocate ca text ISO 8601 | SQLite nu are un tip pentru dată; textul ISO se compară și se ordonează corect. |
| Statisticile „la o dată” folosesc doar meciurile strict anterioare zilei | Exclud meciul țintă și toate meciurile din aceeași zi; sezoanele vechi nu au ora de începere. |
| O singură regulă de tăiere pentru toate statisticile (`_select_before`) | Regula care previne scurgerea de informații există într-un singur loc și este verificată pentru toate statisticile. |
| Index pe echipe și căutare binară în locul filtrării tuturor meciurilor | O(log n + k) pe interogare în loc de O(n); selecția „sezonul până acum” este de circa 120 de ori mai rapidă. |
| Lipsa istoricului este raportată ca „fără date” (`None`), nu ca 0 | Un 0 ar descrie o echipă foarte slabă; fiecare model decide explicit cum tratează echipele noi. |
| Un `MatchHistory` conține o singură competiție | Mediile ligii nu pot amesteca două competiții. |
| Un singur format pentru predicții, verificat la conversie | Toate modelele pot fi comparate direct, iar o predicție invalidă nu poate ajunge în evaluare. |
| Modelul egalurilor din Elo este reantrenat în fiecare luni, ca regresia logistică | Aceeași regulă pentru ambele modele antrenate, definită într-un singur loc. |
| Un model care nu poate prezice un meci lipsește din rezultatul acelui meci | Nu sunt inventate predicții; evaluarea va compara modelele doar pe meciurile prezise de toate. |
| Meciurile ipotetice sunt prezise cu un meci înlocuitor, prin același cod | Interfața și evaluarea nu pot da rezultate diferite; testele arată că scorul fictiv nu are niciun efect. |
