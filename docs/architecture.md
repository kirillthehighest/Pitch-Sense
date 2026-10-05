# Arhitectura aplicației PitchSense

Acest document descrie structura aplicației, fluxul datelor și deciziile tehnice luate până acum (fazele 0–17). Se actualizează ori de câte ori structura se schimbă.

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
| `app/services` | Operațiile cerute de interfață, gata de afișat, cu rezultatele lente păstrate în memorie. Fără Qt. | toate straturile de mai sus |
| `app/visualization` | Construiește graficele din rezultate deja calculate, fără calcule proprii; păstrează culorile aplicației (`palette.py`). | matplotlib, tipurile de rezultate din `app.services` și `app.evaluation` |
| `app/ui` | Interfața grafică: preia datele de intrare, apelează serviciile și afișează rezultatele; identitatea vizuală (`brand.py`, `theme.py`, `assets/`). | PySide6 și celelalte straturi |

## 3. Reguli verificate automat

Testul `tests/test_architecture.py` verifică la fiecare rulare că:

- `app/algorithms` importă doar biblioteca standard și NumPy, nimic din restul aplicației;
- doar `app/ui` importă PySide6;
- matplotlib este importat doar în `app/visualization` și `app/ui`;
- nicio parte a aplicației nu importă scikit-learn, SciPy sau statsmodels;
- `app/services` nu importă Qt; poate fi testat fără nicio fereastră.

## 4. Fluxul datelor

```
data/raw/<cod>/*.csv          fișierele originale, nemodificate (cinci ligi)
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
app/services                  operațiile interfeței, fără Qt
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
| `competitions.py` | Ligile cunoscute: numele, numărul de echipe pe sezon și sezoanele oprite mai devreme (secțiunea 13.1). |
| `build_database.py` | Comanda care reconstruiește baza de date din fișierele brute. |
| `paths.py` | Locul unic în care sunt definite căile către fișierele de date, din codul sursă și dintr-un pachet de instalare (secțiunea 12.2). |

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
- data meciului se încadrează în sezon, între 1 iulie și 31 august a anului următor (din cauza pandemiei, sezonul 2019/20 s-a încheiat în La Liga pe 19 iulie 2020, iar în Serie A pe 2 august 2020);
- nu există meciuri duplicate, iar toate rândurile unui fișier aparțin aceleiași competiții;
- toate problemele dintr-un fișier sunt raportate împreună, fiecare cu numărul liniei.

La construirea bazei de date, fiecare sezon trebuie să fie un campionat complet în sistem tur-retur, cu numărul de echipe al ligii în acel sezon: la 20 de echipe, 380 de meciuri și 38 pe echipă; la 18, 306 și 34. Fiecare echipă găzduiește fiecare adversar o singură dată. Un sezon oprit oficial mai devreme (Ligue 1 2019/20) trebuie să aibă exact meciurile jucate.

### 5.4. Particularități ale fișierelor sursă

- Datele sunt scrise `zz/ll/aa` până în sezonul 2017-18 și `zz/ll/aaaa` începând cu 2018-19.
- Unele fișiere încep cu un marcaj BOM (în La Liga 2024-25 și 2025-26, în Premier League și 2021-22); toate sunt citite cu codificarea `utf-8-sig`.
- Numărul de coloane variază între 61 și 132, deoarece coloanele cu cotele caselor de pariuri se schimbă. De aceea coloanele sunt alese după nume.
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

Rezultat la 2026-10-05: 36.197 de meciuri în cinci ligi și 20 de sezoane fiecare (Premier League, La Liga și Serie A câte 7.600, Bundesliga 6.120, Ligue 1 7.277), toate complete, cu excepția documentată a sezonului Ligue 1 2019/20. Meciurile citite din baza de date sunt identice cu cele încărcate direct din fișierele CSV.

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

Exemple de predicții pentru un singur meci (victorie gazde / egal / victorie oaspeți; rulare din 2026-10-05, cu $N = 76$ pentru modelul Poisson):

| Meci | Elo | Poisson | Regresie logistică | Rezultat |
|---|---|---|---|---|
| Real Madrid – Barcelona, 26.10.2025 | 50,2% / 26,8% / 23,0% | 45,6% / 24,0% / 30,4% (goluri așteptate 1,66–1,31) | 44,3% / 26,5% / 29,3% | 2–1 |
| Barcelona – Real Madrid, 29.11.2010 | 50,8% / 25,5% / 23,6% | 50,7% / 23,7% / 25,6% (1,74–1,17) | 41,5% / 26,0% / 32,6% | 5–0 |
| Barcelona – Oviedo, 01.03.2026 (ipotetic) | 89,2% / 9,2% / 1,6% | 75,8% / 15,1% / 9,1% (2,54–0,77) | 86,1% / 10,4% / 3,5% | nejucat |

Scoaterea meciului Real Madrid – Barcelona din date și cererea lui ca meci ipotetic dau exact aceleași probabilități.

Limitare: `predict_fixture` recalculează toate modelele. Pentru sezoanele recente durează aproximativ 7 s (pentru 2010/11, aproximativ 1 s). De aceea, interfața (Faza 11) calculează o singură dată predicțiile tuturor meciurilor jucate și le reutilizează (secțiunea 9.3).

## 8. Backtesting cronologic (Faza 8)

Comanda `python -m app.evaluation.backtesting` (modulul `app/evaluation/backtesting.py`) produce jurnalul predicțiilor pentru sezoanele de evaluare.

### 8.1. Principiul

Meciurile sunt parcurse în ordinea datelor. Pentru fiecare zi de joc D:

1. modelele antrenate (modelul egalurilor din Elo și regresia logistică) sunt reantrenate în fiecare luni, doar pe meciurile dinaintea acelei zile de luni;
2. fiecare model prezice toate meciurile din ziua D, folosind doar meciurile dinaintea zilei D;
3. abia apoi rezultatele din ziua D devin disponibile: ratingurile Elo se actualizează, iar meciurile intră în istoric.

Aceste reguli sunt aplicate de motorul de predicție (secțiunea 7), iar testele de scurgere a informațiilor le verifică pentru fiecare model.

### 8.2. Ce intră în evaluare

- Doar sezoanele de evaluare, 2010/11–2025/26. Sezonul de încălzire și sezoanele de calibrare sunt excluse.
- Doar meciurile prezise de toate cele trei modele, pentru ca modelele să fie comparate în condiții identice. Meciurile cărora le lipsește un model sunt numărate și raportate.

### 8.3. Referințele (baseline)

Pe lângă cele trei modele, jurnalul conține două referințe, care nu sunt algoritmi ai proiectului, ci arată ce rezultat se obține fără ei:

- **Frecvențele trecute:** frecvențele victoriilor gazdelor, egalurilor și victoriilor oaspeților în ultimul sezon de meciuri ale ligii dinaintea zilei (380 de meciuri la 20 de echipe, 306 la 18). Este o predicție probabilistică completă, fără nicio informație despre echipe.
- **Mereu victoria gazdelor:** probabilitatea 1 pentru victoria gazdelor. Servește doar ca referință pentru acuratețe, pentru că probabilitățile 0 nu pot fi evaluate cu măsuri precum pierderea logaritmică (ar da infinit).

### 8.4. Jurnalul predicțiilor

Fiecare ligă are jurnalul ei, fișierul CSV `data/results/backtest_<cod>.csv` (de exemplu `backtest_SP1.csv`), cu câte un rând pentru fiecare meci și fiecare model:

| Coloană | Conținut |
|---|---|
| `match_date`, `season`, `home_team`, `away_team` | meciul |
| `home_goals`, `away_goals`, `actual` | scorul și rezultatul real (`H`, `D` sau `A`) |
| `model` | Elo, Poisson, Logistic regression, Past frequencies sau Always home win |
| `p_home`, `p_draw`, `p_away` | probabilitățile prezise |
| `predicted` | rezultatul cel mai probabil (la egalitate: gazde, apoi egal) |
| `expected_home_goals`, `expected_away_goals` | golurile așteptate, doar pentru modelul Poisson |
| `home_group`, `away_group` | grupurile K-Means momentane ale echipelor (0 = cel mai puternic, `promoted` = promovată) |

Probabilitățile sunt scrise cu precizie completă, iar citirea fișierului dă exact aceleași valori. Un fișier deteriorat este refuzat cu un mesaj care numește fișierul și linia (secțiunea 11.2). Fișierul nu este inclus în git, pentru că se reconstruiește oricând cu comanda de mai sus.

### 8.5. Rezultatul rulării

Rulare din 2026-10-04: 6.080 de meciuri (2010/11–2025/26) și niciun meci exclus, deci toate meciurile de evaluare au predicții de la toate cele trei modele. Jurnalul are 5 predicții pentru fiecare meci, adică 30.400 de rânduri, și se calculează în aproximativ 8 s. Două rulări consecutive au produs fișiere identice octet cu octet.

Măsurile de evaluare (acuratețea, scorul Brier, pierderea logaritmică, matricea de confuzie, calibrarea și eroarea golurilor așteptate) se calculează din acest jurnal în Faza 9.

### 8.6. Teste

Pe sezoanele de test, testele verifică:

- câte un rând pentru fiecare meci de evaluare și fiecare model, cu probabilități valide și rezultatul real corect;
- rezultatul prezis este cel mai probabil, iar doar rândurile modelului Poisson au goluri așteptate;
- frecvențele trecute calculate de mână: înaintea primului meci de evaluare, liga are 6 victorii ale gazdelor, 4 egaluri și 2 victorii ale oaspeților din 12 meciuri;
- grupurile K-Means din jurnal sunt cele momentane;
- meciurile fără toate cele trei modele sunt excluse și numărate;
- două rulări dau același jurnal, iar salvarea și citirea lui nu pierd nimic.

## 9. Interfața grafică (Faza 11)

Aplicația se pornește cu `python -m app`. Interfața este scrisă cu PySide6 și, din Faza 16, este în limba română (secțiunea 14 și `docs/brand.md`).

### 9.1. Ecranele

Fereastra are o bară de sus cu sigla, cele cinci ecrane și butonul „Echipa ta”, un panou în stânga cu cele cinci ligi și, deasupra fiecărui ecran, un „erou” cu liga și titlul ecranului (secțiunea 14.1). Toate ecranele arată liga aleasă.

| Ecranul | Ce permite |
|---|---|
| Acasă | liga pe scurt, modelul cu cel mai mic scor Brier și dacă avantajul lui față de următorul este real, echipa ta și rezultatele principale ale modelelor; dacă jurnalul predicțiilor lipsește, butonul „Rulează backtestul” îl construiește |
| Predicție | alegerea unui sezon și a unui meci jucat sau a oricăror două echipe din sezon și a unei date; probabilitățile fiecărui model, golurile așteptate, scorurile cele mai probabile, graficul probabilităților scorurilor (Poisson) și rezultatul real, dacă meciul s-a jucat |
| Echipe | clasamentul la o anumită dată sau la final de sezon și profilul unei echipe: poziție, rezultate, acasă și în deplasare, ultimele 5 rezultate, șuturi pe poartă, grupul K-Means de dinaintea sezonului și grupul sezonului încheiat; sub-filele „Clasament”, „Rating Elo” și „Grupuri” |
| Modele | măsurile de evaluare, diferențele reale dintre modele, împărțirea pe sezoane, rezultate și tipuri de meciuri și cât de diferite sunt predicțiile (sub-fila „Tabele”); calibrarea și matricea de confuzie (sub-fila „Grafice”) |
| Ligi | cele cinci ligi comparate: caracterul fiecăreia, scorul Brier al modelelor, diferențele reale dintre modele în fiecare ligă și pe toate la un loc (sub-fila „Tabele”); abilitatea modelelor și avantajul gazdelor (sub-fila „Grafice”); dacă lipsesc jurnale, un buton le construiește |

Graficele sunt descrise în secțiunea 10.

### 9.2. Straturile interfeței

- `app/services/` conține operațiile cerute de interfață, fără Qt: ligile din baza de date și lista sezoanelor, echipelor și meciurilor (`catalog.py`), predicțiile cu memorie (`predictions.py`), analiza echipelor și clasamentul (`teams.py`), rezultatele evaluării unei ligi (`evaluation.py`), comparația ligilor (`leagues.py`), alegerile păstrate între porniri (`preferences.py`) și textul afișat în română (`formatting.py`, `labels.py`). Serviciile sunt testate fără nicio fereastră.
- `app/ui/` conține doar ecranele: preiau alegerile utilizatorului, apelează serviciile și afișează rezultatele. Nu calculează nimic.

### 9.3. Lucrul în fundal

Operațiile lente rulează pe fire de execuție separate (`app/ui/worker.py`), iar rezultatul se întoarce prin semnale Qt pe firul interfeței; firele de lucru nu ating niciodată elementele ferestrei. Orice eroare apare ca mesaj în fereastră, fără ca aplicația să se oprească. Un jurnal al predicțiilor care nu poate fi citit este semnalat direct în ecran, cu butonul „Rulează backtestul” (secțiunea 11.2).

- La pornire, toate predicțiile istorice ale ligii afișate sunt calculate o singură dată (aproximativ 7 s); o ligă aleasă pentru prima dată își pregătește predicțiile la fel, iar bara de stare arată când sunt gata. După aceea, orice meci jucat apare imediat, cu exact aceleași valori ca în evaluare.
- Un meci ipotetic este calculat la cerere (aproximativ 7 s pentru sezoanele recente).
- Jurnalul predicțiilor se construiește la cerere (aproximativ 8 s).

### 9.4. Clasamentul

Echipele sunt ordonate după puncte, apoi după golaveraj, apoi după golurile marcate. Regulile oficiale de departajare diferă de la o ligă la alta (în La Liga, de exemplu, contează mai întâi rezultatele directe) și nu sunt modelate. Nici deducerile oficiale de puncte (de exemplu, în Serie A 2006/07, după scandalul aranjării meciurilor) nu sunt modelate: clasamentul se calculează doar din rezultatele meciurilor.

### 9.5. Verificare

- Ecranele sunt testate fără fereastră vizibilă (`QT_QPA_PLATFORM=offscreen`): fiecare ecran este construit cu datele de test și acționat prin propriile butoane, iar valorile afișate sunt comparate cu cele calculate de mână. Din Faza 16, testele folosesc și o bază de date sintetică cu două ligi (alegerea ligii, „echipa ta” dintr-o altă ligă, ecranul Ligi). Pentru teste, lucrul în fundal este înlocuit cu o execuție imediată, cu același contract.
- Un test separat folosește firele de execuție reale și verifică faptul că rezultatul ajunge pe firul interfeței.
- Toate ecranele au fost desenate cu datele reale și verificate vizual; aplicația a fost pornită într-o fereastră obișnuită pe macOS și a rulat fără erori.

## 10. Graficele (Faza 12)

### 10.1. Ce arată fiecare grafic

| Grafic | Unde apare | Ce arată | De unde vin datele |
|---|---|---|---|
| Evoluția ratingului Elo | Echipe, sub-fila „Rating Elo” | ratingul echipei înaintea fiecăruia dintre meciurile ei, câte o linie pe sezon; golurile dintre linii sunt vacanțele de vară și sezoanele petrecute în afara ligii; sezonul ales este evidențiat cu auriu, iar data aleasă (dacă nu este ales sezonul întreg) este marcată cu o linie verticală | `TeamService.elo_history`: exact ratingurile folosite de predicțiile Elo, calculate doar din meciurile zilelor anterioare |
| Probabilitățile scorurilor | Predicție | probabilitatea Poisson a fiecărui scor de la 0-0 la 6-6 | tabelul scorurilor din predicția Poisson (calculat până la 20 de goluri pe echipă; scorurile mai mari nu sunt afișate) |
| Calibrarea | Modele, sub-fila „Grafice” | pentru fiecare model, frecvența observată în funcție de probabilitatea prezisă, pe 10 intervale, cu toate rezultatele la un loc; diagonala înseamnă calibrare perfectă; intervalele goale sunt omise | tabelele de calibrare ale evaluării (Faza 9) |
| Matricea de confuzie | Modele, sub-fila „Grafice” | numărul de meciuri după rezultatul real (rânduri) și cel prezis (coloane), pentru modelul ales din listă | evaluarea (Faza 9) |
| Grupurile echipelor | Echipe, sub-fila „Grupuri” | echipele sezonului după golurile marcate și primite pe meci, colorate după grupul K-Means, cu centrele grupurilor (✕) și echipa aleasă încercuită | `TeamService.season_groups`: grupurile descriptive din Faza 6, aceleași ca „Grupul sezonului” din profilul echipei |
| Abilitatea modelelor (Faza 16) | Ligi, sub-fila „Grafice” | pentru fiecare ligă și model, partea din scorul Brier al frecvențelor trecute eliminată de model (scorul de abilitate Brier), în bare orizontale | `LeagueResults.skill` (`app/evaluation/leagues.py`) |
| Avantajul gazdelor (Faza 16) | Ligi, sub-fila „Grafice” | pentru fiecare ligă, procentul victoriilor gazdelor în 2020/21 (sezon jucat în mare parte fără spectatori) și în celelalte sezoane de evaluare, unite printr-o linie | `LeagueCharacter` (`app/evaluation/leagues.py`); o ligă fără ambele valori este omisă |

### 10.2. Axele graficului grupurilor

Echipa a ales două mărimi ușor de citit: golurile marcate și golurile primite pe meci. K-Means folosește însă șase mărimi (secțiunea 5 din `docs/algorithms/kmeans.md`), deci pe aceste două axe o echipă poate apărea mai aproape de centrul altui grup. Pe datele reale, 134 din cele 400 de profiluri (33,5%) sunt mai aproape, pe grafic, de centrul altui grup decât al propriului grup (de exemplu, în 2015/16: Sociedad și Valencia, din grupul „Slabă peste tot”, apar lângă centrul grupului „Jumătatea de jos, puternică acasă”). Graficul și nota din filă precizează că grupurile folosesc toate cele șase mărimi.

Varianta respinsă, PCA (proiecția celor șase mărimi pe două axe), ar fi arătat mai bine structura, dar axele nu ar fi avut un înțeles direct și ar fi adăugat o metodă nouă, care trebuia implementată și documentată.

Grupurile sunt arătate doar pentru un sezon întreg, pentru că profilurile descriu sezonul încheiat; pentru o dată din timpul sezonului, sub-fila afișează un mesaj.

### 10.3. Construcție

- `app/visualization/charts.py` conține șapte funcții (două adăugate în Faza 16) care primesc rezultate deja calculate și întorc o figură matplotlib (`Figure`). Ele doar desenează: nu calculează nimic din date (singurul calcul așază numele echipelor pe graficul grupurilor, secțiunea 11.4) și nu folosesc `pyplot`, deci nu există stare globală, iar aceeași figură poate fi afișată în aplicație sau salvată într-un fișier.
- Datele vin din servicii: `TeamService` are două metode noi (`elo_history`, `season_groups`), iar rezumatul predicției Poisson include tabelul complet al scorurilor (`ModelSummary.score_probabilities`). Rularea Elo este făcută o singură dată și păstrată în memorie (aproximativ 0,02 s pe toate datele).
- Interfața afișează figurile prin `ChartView` (`app/ui/widgets.py`), care folosește pânza Qt a matplotlib (`FigureCanvasQTAgg`) și arată un mesaj cât timp nu există un grafic. Nu a fost necesară nicio bibliotecă nouă.
- Din Faza 16, fiecare figură este construită în stilul PitchSense: fundalul întunecat al cardurilor, titlurile cu Barlow Condensed, textul cu Libre Franklin, culorile din `palette.py`, grile subțiri, zecimale cu virgulă. Stilul este aplicat doar figurii respective (`rc_context`), fără a schimba setările globale ale matplotlib. Regulile sunt în `docs/brand.md`, secțiunea 6.

### 10.4. Verificare

- `tests/test_charts.py`: fiecare grafic desenează exact valorile primite (datele liniilor, celulele, barele, textele, etichetele, culorile și legenda) și se salvează ca imagine PNG fără avertismente; datele invalide sunt refuzate; numele unor echipe aflate aproape una de alta nu se suprapun; gradațiile axelor arată exact valoarea lor.
- `tests/test_services.py`: istoricul Elo coincide cu ratingurile folosite de predicții și nu se schimbă dacă se schimbă scorul meciului însuși; grupurile coincid cu cele din prezentarea echipei.
- `tests/test_ui.py`: fiecare ecran arată un mesaj înainte de rezultate și graficele după ele; o componentă `ChartView` conține mereu exact un grafic sau un mesaj.
- Graficele au fost desenate cu datele reale și verificate vizual, atât fără fereastră, cât și într-o fereastră macOS obișnuită (ecran Retina, mod întunecat), cu lucrul în fundal real.

### 10.5. Limitări

- Pe graficul grupurilor, numele echipelor foarte apropiate se mai pot suprapune când graficul este mic (secțiunea 11.4).
- Interfața și graficele au doar tema întunecată, și când sistemul folosește modul luminos (`docs/brand.md`, secțiunea 9).
- Graficul scorurilor arată doar scorurile de până la 6 goluri pe echipă.

## 11. Testarea de integrare și verificarea pe datele reale (Faza 13)

### 11.1. Teste de la un capăt la altul

`tests/test_integration.py` rulează tot lanțul pe cele două sezoane sintetice din `tests/conftest.py`: fișierele CSV brute → baza de date → jurnalul predicțiilor → evaluarea → fereastra aplicației. Testele verifică faptul că straturile spun același lucru:

- pentru fiecare dintre cele 12 meciuri ale sezonului evaluat, ecranul Predicție afișează exact probabilitățile, rezultatul cel mai probabil și golurile așteptate din jurnal;
- tabelele din ecranele Acasă și Modele afișează exact măsurile calculate de evaluator din jurnal;
- clasamentul ambelor sezoane coincide cu un clasament calculat direct din rândurile fișierelor CSV.

Sunt verificate și căile de eroare: lipsa bazei de date la pornire (mesaj cu comanda `python -m app.data.build_database` și codul de ieșire 1), un jurnal deteriorat și un backtest care eșuează în timpul rulării. Aplicația Qt, serviciile peste baza de date sintetică și colectorul de erori folosite de testele interfeței sunt definite o singură dată, în `tests/conftest.py`.

### 11.2. Jurnalul deteriorat

Testele au găsit două probleme, corectate:

- Un jurnal deteriorat dădea mesaje neclare (de exemplu `'match_date'`). Acum `read_log` numește problema, fișierul și linia (de exemplu `backtest_SP1.csv, line 4: expected 16 values`), iar serviciul de evaluare adaugă „Run the backtest again to rebuild it.” Din Faza 16, ecranele pun înaintea acestor detalii tehnice o explicație în română.
- Dacă fișierul jurnalului exista, dar nu putea fi citit, ecranele cu rezultate ascundeau butonul de backtest, deci jurnalul nu putea fi reconstruit din aplicație, iar fiecare schimbare de ecran ar fi repetat mesajul de eroare. Acum ecranele Acasă, Modele și Ligi arată problema direct în pagină, fără ferestre de dialog, iar butonul reconstruiește jurnalul.

### 11.3. Verificarea pe datele reale

Rulare din 2026-10-04:

- Baza de date a fost reconstruită din cele 20 de fișiere: toate sezoanele sunt complete (7.600 de meciuri).
- Jurnalul predicțiilor reconstruit este identic, byte cu byte, cu cel anterior (30.400 de rânduri; pe alt sistem de operare pot diferi ultimele cifre, secțiunea 12.5).
- Calibrările (Elo, Poisson, regresia logistică) și alegerea lui $k$ dau exact valorile înregistrate.
- Toate valorile obținute din date și citate în `README.md` și în `docs/` au fost recalculate. Trei pasaje erau inexacte și au fost corectate: câștigul mediu al echipelor promovate din `docs/algorithms/elo.md` (10,6 puncte de rating și 24 de echipe în scădere, nu 9,8 și 23: calculul vechi se oprea înaintea ultimului meci al fiecărei echipe), precizarea egalității de puncte din 2006/07 în același document și trei afirmații din `docs/comparison.md` (legătura dintre egaluri și sezoanele grele, perechile de grupuri cele mai grele și numărul meciurilor cu echipe promovate dintre cele mai mari diferențe).
- Nu au putut fi recalculate valorile care depind de cod schimbat între timp (predicțiile Elo dinaintea corecției din Faza 9, setările de probă ale modelului Poisson) și durata interogărilor din secțiunea 6.4. Celelalte durate măsurate (backtest 7,9 s, toate predicțiile 6,8 s, un meci ipotetic 6,8 s, modelul Poisson 0,63 s) corespund documentației.
- Cerințele din `AGENTS.md`: fiecare document de algoritm are toate secțiunile cerute, există toate modulele de test cerute și teste de scurgere a informațiilor pentru fiecare model. Lipseau două teste cerute, adăugate acum: regresia logistică pe un set de date separabil și Elo cu numai egaluri.

### 11.4. Numele echipelor pe graficul grupurilor

Numele sunt așezate automat. Fiecare nume încearcă, în ordine, 20 de poziții în jurul punctului său și o alege pe prima care rămâne în interiorul graficului și nu acoperă un nume deja așezat, legenda, un centru de grup sau un alt punct. Dacă nu există o asemenea poziție, o alege pe cea mai puțin rea: acoperirea unui punct contează mai puțin decât acoperirea unui text sau a unui centru. Numele echipei alese este așezat primul.

Pozițiile depind de mărimea figurii, așa că sunt alese din nou ori de câte ori fereastra redimensionează graficul. În Faza 13 erau 14 poziții, la distanțe fixe în puncte, potrivite pentru fontul implicit al matplotlib. Libre Franklin (Faza 16) are rândul cu aproximativ 30% mai înalt, așa că pozițiile de deasupra și de dedesubt ajunseseră să se suprapună între ele, iar un test a semnalat suprapuneri la o figură mică. Acum distanțele pe verticală sunt măsurate în înălțimi ale numelui însuși, deci se potrivesc oricărui font, și s-au adăugat șase poziții mai depărtate.

Pe datele reale (2026-10-05, toate cele cinci ligi, 99 de sezoane cu statistici de șuturi, cu stilul întunecat și titlurile Barlow Condensed), la mărimea implicită a figurii (6,4 × 4,8 țoli) rămâne o singură pereche de nume suprapuse (în La Liga), iar la mărimea graficului din fereastra aplicației (aproximativ 6,0 × 5,5 țoli, la mărimea inițială a ferestrei) nu rămâne niciuna; niciun nume nu acoperă un centru. Pentru asta, graficele ecranului Echipe au cel puțin 540 de pixeli înălțime: la 485 de pixeli rămâneau două perechi. Construirea graficului durează aproximativ 0,1 s.

## 12. Pachetele de instalare (Faza 14)

### 12.1. Construcție

- **PyInstaller 6.22.3** (dependență de dezvoltare) adună interpretorul Python, bibliotecile, codul și datele într-un folder cu un program executabil; pe macOS, folderul devine aplicația `PitchSense.app`. A fost ales în locul lui `pyside6-deploy`, care compilează totul în C cu Nuitka, cere un compilator și construiește mult mai încet.
- `packaging/pitchsense.spec` descrie pachetul. `packaging/build.py` reconstruiește baza de date și jurnalele predicțiilor din fișierele brute, desenează iconița aplicației (din Faza 17), rulează PyInstaller și face arhiva: o imagine `.dmg` pe macOS (cu aplicația și o scurtătură spre `Applications`) și un fișier `.zip` pe Windows.
- PyInstaller nu poate construi pentru alt sistem decât cel pe care rulează: pachetul macOS se construiește pe un Mac, iar cel pentru Windows pe o mașină Windows oferită de GitHub (secțiunea 12.4).
- Pachetul macOS are 68 MB (aplicația despachetată, 144 MB) și cere un Mac cu Apple Silicon și macOS 14 sau mai nou: bibliotecile NumPy incluse sunt construite pentru macOS 14, iar aplicația declară această limită (`LSMinimumSystemVersion`), ca macOS-ul mai vechi să refuze clar pornirea. Pachetul Windows are 84 MB (folderul despachetat, 188 MB) și cere Windows 10 sau 11 pe 64 de biți. Cea mai mare parte din mărime o ocupă Qt, NumPy, pandas și matplotlib.

### 12.2. Fișierele într-un pachet

Un pachet nu trebuie modificat (pe macOS, modificarea aplicației o poate strica), deci aplicația scrie doar în folderul utilizatorului: `~/Library/Application Support/PitchSense` pe macOS și `%LOCALAPPDATA%\PitchSense` pe Windows. Toate căile vin din `app/data/paths.py`:

| Fișier | Din codul sursă | Într-un pachet |
|---|---|---|
| baza de date | `data/pitchsense.db` | în pachet, doar pentru citire |
| jurnalele predicțiilor | `data/results/` | în folderul utilizatorului; la prima pornire, jurnalele din pachet sunt copiate acolo; în aceeași versiune, un jurnal reconstruit de utilizator nu este înlocuit, iar după o actualizare jurnalele versiunii vechi sunt înlocuite (secțiunea 12.7) |
| fonturile și iconițele interfeței | `app/ui/assets/` | în pachet, doar pentru citire |
| alegerile utilizatorului (liga, echipa ta) | `preferences.json`, în folderul utilizatorului | la fel |
| memoria fonturilor matplotlib | `~/.matplotlib` | în folderul utilizatorului (`matplotlib/`) |

Construirea a scos la iveală o problemă: PyInstaller îi dă lui matplotlib un folder temporar nou la fiecare pornire (necesar pentru pachetele dintr-un singur fișier, care se despachetează de fiecare dată în alt loc), așa că memoria fonturilor, care se construiește în aproximativ 18 s pe Mac-ul de test, s-ar fi refăcut la fiecare pornire. Pachetul nostru este un folder care nu se mută, deci punctul de intrare (`app/__main__.py`) păstrează această memorie în folderul utilizatorului. Prima pornire durează aproximativ 30 s, următoarele aproximativ 10 s.

### 12.3. Autoverificarea (`--self-test`)

`python -m app --self-test`, sau programul din pachet pornit cu `--self-test`, deschide fereastra fără a o afișa, pe datele reale, folosește fiecare ecran prin propriile butoane (construind jurnalele care lipsesc), desenează cele șapte grafice, verifică cele două fonturi și iconițele SVG ale interfeței și se termină cu codul 0 dacă toate cele 20 de verificări au reușit (13 până în Faza 16; `app/ui/self_test.py`). Este singura verificare automată posibilă pentru un pachet, în care testele nu pot rula. Raportul este afișat în terminal; o aplicație Windows nu are consolă, așa că acolo raportul este scris în `self-test.txt`, în folderul utilizatorului.

### 12.4. Pachetul pentru Windows (GitHub Actions)

Fluxul `.github/workflows/package.yml` rulează pe o mașină Windows oferită de GitHub: instalează Python 3.14 și dependențele fixate, rulează toate testele și verificarea codului, construiește pachetul cu `packaging/build.py`, pornește autoverificarea pachetului și păstrează fișierul `.zip` 30 de zile, ca *artifact*. Fluxul pornește manual (*Run workflow* pe pagina *Actions*, sau `gh workflow run "Windows package"`) sau la publicarea unei etichete de versiune (`v*`). Depozitul este privat, deci fiecare rulare consumă din minutele gratuite lunare ale contului (o rulare a durat aproximativ 4 minute, care se socotesc dublu pentru Windows).

### 12.5. Verificare

Rulări din 2026-10-05:

- **macOS** (Mac cu Apple Silicon, macOS 27): autoverificarea pachetului a trecut (13 din 13 verificări; prima pornire 29 s, a doua 10 s), inclusiv pornit direct din imaginea `.dmg` montată doar pentru citire, ceea ce arată că aplicația nu scrie nimic în pachet; pornită normal (`open PitchSense.app`), aplicația rulează și folosește aproximativ 320 MB de memorie.
- **Windows** (mașina `windows-latest` de la GitHub): toate cele 525 de teste, verificarea codului, construirea pachetului și autoverificarea acestuia (13 din 13) au trecut; rularea a durat 3 min 54 s. Testele nu rulaseră niciodată pe Windows până acum.
- **Între sisteme:** jurnalul predicțiilor construit pe Windows diferă de cel construit pe macOS doar în ultima cifră a unor probabilități (cel mult $3{,}3 \cdot 10^{-16}$), din cauza bibliotecilor numerice diferite. Toate cele 30.400 de rezultate prezise, toate măsurile raportate (cu 4 zecimale), matricele de confuzie și diferențele dintre modele sunt identice.
- **Teste noi:** `tests/test_paths.py` (folderul utilizatorului pe fiecare sistem, copierea jurnalului, memoria fonturilor, pornirea cu o copiere eșuată) și `tests/test_self_test.py`.
- **Neverificat:** pachetul pentru Windows nu a fost deschis de o persoană pe un calculator cu Windows, ci doar autoverificat, fără fereastră vizibilă, pe mașina GitHub; pachetul macOS nu a fost încercat pe alt Mac sau după descărcarea din internet.

### 12.6. Limitări

- Pachetele nu sunt semnate (semnarea cere un abonament Apple Developer de 99 USD pe an și, pentru Windows, un certificat de semnare a codului), deci ambele sisteme avertizează la prima deschidere; `README.md` explică pașii.
- Pachetul macOS rulează doar pe Mac-uri cu Apple Silicon; pentru Mac-urile cu procesor Intel ar trebui construit pe un Mac cu Intel.
- Prima pornire durează aproximativ 30 s.
- În macOS 27, comanda `hdiutil` folosită pentru imaginea `.dmg` afișează un avertisment că este învechită, dar funcționează; comanda care o înlocuiește (`diskutil image`) nu există pe versiunile mai vechi de macOS.

### 12.7. Versiunea 0.2.0 (Faza 17)

Pachetele versiunii 0.2.0 conțin cinci ligi, noua interfață și noua siglă. Față de 0.1.0 s-au schimbat:

- **Versiunea** este scrisă într-un singur loc, `app/__init__.py` (`__version__`). De acolo o citesc `pyproject.toml`, pachetele (numele fișierelor și `CFBundleShortVersionString`) și fereastra, care o afișează în panoul din stânga.
- **Conținutul pachetului:** baza de date cu cele cinci ligi, jurnalele celor cinci ligi, fonturile și iconițele interfeței.
- **Iconița aplicației** este desenată din siglă la fiecare construire. `packaging/icons.py` salvează imaginile PNG ale lui `icon_image` în formatele pe care le citesc sistemele: `PitchSense.icns` pentru macOS (unsprezece imagini, de la 16 la 1024 de pixeli) și `PitchSense.ico` pentru Windows (șapte imagini, de la 16 la 256 de pixeli). Ambele formate primesc PNG direct, deci nu este nevoie de o bibliotecă nouă. Testele (`tests/test_icons.py`) citesc înapoi fișierele, iar `iconutil`, unealta macOS, desface fișierul `.icns` fără erori.
- **Actualizarea.** Jurnalele construite de o versiune mai veche arată rezultatele vechilor modele: jurnalul La Liga din 0.1.0 a fost calculat cu $N = 38$ pentru Poisson, înainte ca Faza 15 să-l schimbe în 76. Regula de copiere de până acum („un jurnal existent nu este înlocuit niciodată”) le-ar fi păstrat după actualizare. Acum folderul utilizatorului are un fișier `VERSION` cu versiunea jurnalelor din el (`copy_bundled_results` din `app/data/paths.py`):
  - Dacă fișierul lipsește (cazul lui 0.1.0, care nu-l scria) sau arată altă versiune, toate jurnalele din pachet le înlocuiesc pe cele vechi.
  - În aceeași versiune, un jurnal reconstruit de utilizator este păstrat, pentru că același cod îl reconstruiește la fel.
  - Celelalte fișiere ale utilizatorului (alegerile, memoria fonturilor) nu sunt atinse.

Verificare (2026-10-06):

- **macOS** (Mac cu Apple Silicon, macOS 27): `python packaging/build.py` a construit pachetul în aproximativ 90 s.
  - Mărimea: imaginea `.dmg` are 74 MB, aplicația despachetată 163 MB.
  - Autoverificarea pachetului a trecut (20 din 20, cu ambele fonturi și iconițele SVG), atât din `dist/`, cât și din imaginea `.dmg` montată doar pentru citire.
  - Folderul utilizatorului de pe Mac-ul de test avea jurnalul La Liga lăsat de pachetul 0.1.0 și niciun fișier `VERSION`. Prima pornire a lui 0.2.0 l-a înlocuit cu jurnalul nou (identic, după sumele de control, cu cel construit), a adăugat celelalte patru și a scris `VERSION`.
  - Pornită normal (`open PitchSense.app`), aplicația rulează, folosește aproximativ 450 MB de memorie și se închide fără erori.
- **Windows** (fluxul „Windows package” pe mașina `windows-latest` de la GitHub, ramura `phase-17`): toate cele 662 de teste și verificarea codului au trecut, pachetul `.zip` are 88 MB, iar autoverificarea pachetului a trecut (20 din 20, cu ambele fonturi și iconițele SVG). Lucrarea a durat 7 min, după aproximativ 5 min de așteptare la coadă.

## 13. Cinci ligi (Faza 15)

### 13.1. Datele

Pe lângă La Liga (`SP1`) sunt incluse Premier League (`E0`), Serie A (`I1`), Bundesliga (`D1`) și Ligue 1 (`F1`), fiecare cu sezoanele 2006/07–2025/26, din aceeași sursă: în total 36.197 de meciuri (`data/raw/README.md`). `app/data/competitions.py` descrie fiecare ligă: numele, numărul obișnuit de echipe și abaterile de la el, verificate pe fișiere:

- Bundesliga are 18 echipe (306 meciuri pe sezon).
- Ligue 1 are 20 de echipe până în 2022/23 și 18 din 2023/24. Sezonul 2019/20 a fost oprit după 279 de meciuri din cauza pandemiei de COVID-19 (clasamentul a fost stabilit după punctele pe meci); pentru acest sezon, verificarea cere exact meciurile jucate și nicio echipă peste un sezon complet.
- Serie A 2019/20 s-a încheiat pe 2 august 2020, așa că fereastra de date a unui sezon merge acum până la 31 august.
- Ligue 1 2006/07 nu are deloc statistici de șuturi, iar în cinci alte sezoane lipsesc la 1–2 meciuri. Statisticile sunt opționale: unde lipsesc, regresia logistică folosește media ligii, iar K-Means nu poate face profilul sezonului respectiv (îl sare; vezi secțiunea 13.3).

### 13.2. Setările modelelor pentru fiecare ligă

`app/prediction/settings.py` păstrează setările fiecărei ligi, grupate pe model: `EloSettings` (K, H), `PoissonSettings` (N, m și fereastra ligii) și `LogisticSettings` (L2, Elo-ul folosit pentru caracteristica diferenței Elo și ferestrele caracteristicilor). Ferestrele de „un sezon” urmează mărimea obișnuită a ligii: 380 de meciuri și 19 meciuri acasă pe echipă la 20 de echipe, 306 și 17 la 18 echipe. Apelat fără setări, fiecare model le folosește pe cele ale ligii meciurilor sale; o ligă fără setări calibrate produce o eroare, nu o valoare ghicită.

Valorile sunt alese de `python -m app.evaluation.league_calibration`, pe sezonul de încălzire și pe sezoanele de calibrare ale fiecărei ligi, cu aceleași grile și reguli pentru toate (`docs/leagues.md`). Grila lui $N$ a fost extinsă la cinci sezoane, pentru că Premier League și Bundesliga își alegeau valoarea maximă; cu aceeași regulă, La Liga a primit $N = 76$ în loc de 38 (`docs/algorithms/poisson.md`, secțiunea 7.3).

### 13.3. Evaluarea și comparația ligilor

`python -m app.evaluation.backtesting` scrie câte un jurnal pentru fiecare ligă (`data/results/backtest_<cod>.csv`), cu setările ei; `python -m app.evaluation.evaluator <cod>` și `python -m app.evaluation.comparison <cod>` analizează o ligă, iar `python -m app.evaluation.leagues` compară ligile între ele (`app/evaluation/leagues.py`). Rezultatele sunt în `docs/leagues.md`.

Grupurile K-Means folosesc doar sezoanele cu statistici de șuturi. Dacă sezonul dinaintea unui sezon nu are statistici (Ligue 1 2007/08), echipele nu primesc grup înainte de sezon, iar ecranul echipei spune că informația nu este disponibilă.

### 13.4. Verificare

- Teste noi: `tests/test_competitions.py`, `tests/test_settings.py`, `tests/test_league_calibration.py` și `tests/test_leagues.py` (caracterul unei ligi calculat de mână, scorul de abilitate, comparația pe toate ligile la un loc ca medie ponderată a ligilor), plus teste pentru un sezon oprit mai devreme, pentru schimbarea numărului de echipe, pentru un sezon încheiat în august, pentru sezoanele fără statistici, pentru setările implicite ale fiecărei ligi și pentru grila lui $N$.
- Pe datele reale (2026-10-05): toate cele 100 de sezoane trec verificările la construirea bazei de date; după trecerea la setări pe ligă, dar înainte de schimbarea lui $N$, jurnalul La Liga a rămas identic byte cu byte; niciun meci de evaluare al vreunei ligi nu a fost exclus; autoverificarea aplicației trece.

## 14. Identitatea vizuală și interfața în română (Faza 16)

Semnul, culorile, literele și regulile interfeței sunt descrise, cu motivele lor, în `docs/brand.md`. Această secțiune descrie structura.

### 14.1. Ce s-a schimbat

Faza a avut mai multe variante. Prima (deschisă la culoare, cu un semn neutru) a fost înlocuită la cererea echipei cu tema întunecată și culorile blaugrana de acum, după modelul site-ului FC Barcelona, al LiveScore și al OneFootball. Stema de club desenată pentru ea a semănat prea mult cu cea a Barcelonei, așa că a fost înlocuită de monograma PS; echipa a ales varianta minimalistă, fără minge (`docs/brand.md`, secțiunile 1–2).

- **Fereastra** (`app/ui/main_window.py`) are următoarele părți:
  - **bara de sus**: sigla cu numele PITCHSENSE, cele cinci ecrane (Acasă, Predicție, Echipe, Modele, Ligi, cu majuscule, cel ales subliniat cu auriu) și butonul „Echipa ta”;
  - **linia albastru–grena** de sub bară;
  - **panoul ligilor** din stânga („COMPETIȚII”, câte un buton cu steag și țară pentru fiecare ligă, `LeagueButton`);
  - **eroul** (`HeroBanner`): gradient de noapte, liniile terenului, liga cu steag și titlul ecranului.

  Ecranele stau sub erou, în zone care se derulează.
- **Ligile în aplicație.** Liga se alege din panoul din stânga sau dintr-un card de ligă al ecranului Ligi, iar toate ecranele o arată. Serviciile unei ligi (catalog, predicții, echipe, evaluare) sunt deschise prima dată când liga este aleasă și apoi păstrate (`AppContext.league` în `app/ui/context.py`). Ecranul **Ligi** (`app/ui/leagues.py`) compară cele cinci ligi, cu datele din `app/services/leagues.py`. Liga afișată la închidere este afișată și la următoarea pornire.
- **Echipa ta.** Utilizatorul își alege o echipă, păstrată între porniri (`app/services/preferences.py`). Echipa este evidențiată în clasamente și aleasă din start în Predicție și Echipe (`docs/brand.md`, secțiunea 5.2).
- **Ecranul Acasă** (`app/ui/home.py`) a înlocuit Dashboard.
  - Are patru cifre mari (`StatTile`) și cardul echipei tale, cu ecuson și ultimele cinci rezultate (`FormStrip`).
  - Nu mai numește „cel mai bun model” doar după cel mai mic scor Brier: spune și dacă diferența față de următorul model este reală. În La Liga, de exemplu, Elo (0,5776) și regresia logistică (0,5777) nu diferă real.
- **Cardul meciului** (ecranul Predicție) are ecusoanele echipelor, scorul și câte o bară de probabilitate pe model (`ProbabilityBars`). Cifrele exacte rămân și într-un tabel.
- **Limba.** Tot textul afișat este în română, cu numerele scrise românește (`app/services/formatting.py`, `labels.py`). Jurnalele și codul își păstrează identificatorii în engleză.
- **Aspectul** stă în câteva fișiere:
  - foaia de stil, paleta Qt și fonturile: `app/ui/theme.py`;
  - sigla, iconița, steagurile și ecusoanele: `app/ui/brand.py`, desenate cu QPainter;
  - piesele desenate ale ecranelor: `app/ui/widgets.py`;
  - fișierele fonturilor și iconițele: `app/ui/assets/`;
  - culorile: `app/visualization/palette.py`.

### 14.2. Corecții găsite pe parcurs

- Butonul de backtest din ecranul de rezultate construia mereu jurnalul La Liga, oricare ar fi fost liga, pentru că serviciul de evaluare avea liga fixată în cod. Greșeala nu se vedea cât timp interfața arăta doar La Liga. Acum `EvaluationService` primește liga (`competition`), iar un test verifică faptul că jurnalul unei ligi conține echipele ei.
- Numele echipelor de pe graficul grupurilor erau așezate pe distanțe potrivite pentru vechiul font (secțiunea 11.4).
- Prima culoare a egalului din barele de probabilitate stătea prea aproape de grena pentru daltonism (3,5); a fost luminată (secțiunea 6 din `docs/brand.md`).
- Gradațiile cu o zecimală puteau rotunji valoarea (1,25 apărea ca „1,2”); acum gradațiile sunt la distanțe de 1, 2 sau 5 unități și au exact câte zecimale le trebuie.

### 14.3. Verificare

Rulări din 2026-10-05:

- **Teste.** Toate cele 655 de teste trec; `ruff check` și `ruff format --check` nu găsesc nimic. Fișiere de test noi: `tests/test_brand.py` (sigla, iconița, steagurile, ecusoanele, fonturile, contrastele) și `tests/test_formatting.py` (scrierea românească, numele modelelor, prescurtările echipelor, țările). Testele interfeței (`tests/test_ui.py`), de la un capăt la altul (`tests/test_integration.py`), ale autoverificării, ale graficelor și ale serviciilor au fost actualizate și extinse: navigarea, alegerea ligii din panou și din cardurile ligilor, „echipa ta”, cardul meciului, ecranul Ligi, preferințele, comparația ligilor și piesele desenate.
- **Autoverificarea** pe datele reale: 20 din 20.
- **Verificare vizuală.** Toate ecranele și sub-filele au fost desenate fără fereastră, cu datele reale, și verificate vizual, în ambele variante. Au fost găsite și corectate, printre altele:
  - indicatorii butoanelor radio și ai casetelor de bifat erau invizibili;
  - numele modelelor erau tăiate în tabelul predicției;
  - graficele se întindeau pe toată înălțimea paginii de tabele;
  - legendele așezate sub axe erau tăiate;
  - butoanele rotunjite își pierdeau colțurile când raza depășea jumătatea înălțimii;
  - cardurile din stânga ecranului Predicție se întindeau pe toată coloana.
- **Culori.** Paletele graficelor și barele de probabilitate au fost verificate cu validatorul de palete, în modul întunecat (`docs/brand.md`, secțiunea 6).
- **Pornire.** Aplicația a fost pornită pe macOS (`python -m app`) și a rulat 15 s fără erori. Fereastra obișnuită nu a fost inspectată vizual în această fază; imaginile verificate sunt cele desenate fără fereastră.

### 14.4. Limitări

- Doar tema întunecată.
- Echipele au ecusoane cu inițiale, nu stemele lor (stemele sunt mărci înregistrate).
- Pachetele de instalare nu au fost reconstruite în această fază: fonturile, iconițele, iconița aplicației și jurnalele celor cinci ligi trebuie incluse în pachete (Faza 17). Pachetul Windows nu a fost încercat cu noua interfață.

## 15. Setul de date și perioadele

Sursa datelor este Football-Data.co.uk: cinci ligi (Premier League, La Liga, Serie A, Bundesliga, Ligue 1), fiecare cu 20 de sezoane încheiate, 2006/07–2025/26 (36.197 de meciuri). Perioadele sunt aceleași pentru toate ligile.

| Perioadă | Rol |
|---|---|
| 2006/07 | Încălzire: construiește ratingurile și istoricul; nu este evaluată. |
| 2007/08–2009/10 | Calibrare: se aleg hiperparametrii; rezultatele nu sunt raportate. |
| 2010/11–2025/26 | Evaluarea raportată: 16 sezoane; 6.080 de meciuri în fiecare ligă cu 20 de echipe, 4.896 în Bundesliga, 5.757 în Ligue 1; 28.893 în total. |

## 16. Tehnologii

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
| PyInstaller | 6.22.3 | construirea pachetelor de instalare |
| Libre Franklin (font, SIL Open Font License 1.1) | cinci grosimi statice | textul interfeței și al graficelor, inclus în `app/ui/assets/fonts/` |
| Barlow Condensed (font, SIL Open Font License 1.1) | patru grosimi statice | titlurile, cifrele mari, scorul și navigarea, inclus în `app/ui/assets/fonts/` |

## 17. Decizii tehnice

| Decizie | Motiv |
|---|---|
| Python 3.14 | Este cea mai nouă versiune suportată de PySide6 6.11, care cere Python < 3.15. |
| `PySide6-Essentials` în locul pachetului complet `PySide6` | Conține modulele Qt de care avem nevoie (QtCore, QtGui, QtWidgets). Pachetul complet adaugă circa 330 MB de module nefolosite (web, 3D, multimedia), iar graficele sunt realizate cu matplotlib. |
| `pyproject.toml` cu versiuni fixe (`==`), mediu virtual `.venv` și `pip` | Aceleași versiuni pe macOS și Windows. Actualizările se fac intenționat și sunt urmate de rularea tuturor testelor. |
| ruff, fără verificator static de tipuri | Un singur instrument rapid pentru stil și erori frecvente. Adnotările de tip rămân obligatorii. |
| Avertismentele sunt tratate ca erori în teste | Schimbările de API din pandas 3 și NumPy 2 sunt observate imediat, nu ignorate. |
| Interfața în română (din Faza 16); codul și comentariile în engleză; documentația și raportul în română | Decizia echipei: aplicația este prezentată colegilor și profesorilor din UTM. Până în Faza 15, interfața era în engleză. |
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
| Evaluarea folosește doar meciurile prezise de toate cele trei modele | Modelele sunt comparate pe exact aceleași meciuri; pe datele reale nu este exclus niciun meci. |
| Două referințe: frecvențele trecute și „mereu victoria gazdelor” | Arată ce se obține fără algoritmi; a doua este folosită doar pentru acuratețe. |
| Jurnalul predicțiilor este un fișier CSV reconstruit de o comandă și nu este inclus în git | Rezultatele sunt reproductibile, iar fișierele derivate nu se amestecă cu datele brute. |
| Un strat de servicii fără Qt (`app/services/`) între interfață și restul aplicației | Ecranele nu calculează nimic, iar operațiile lor pot fi testate fără fereastră. |
| Predicțiile istorice sunt calculate o dată la pornire și păstrate în memorie | Orice meci jucat apare imediat, cu exact aceleași valori ca în evaluare. |
| Operațiile lente rulează în fundal, iar rezultatul revine prin semnale Qt | Interfața nu se blochează, iar firele de lucru nu ating ferestrele. |
| Testele interfeței rulează fără fereastră și fără biblioteci noi (fără pytest-qt) | Ecranele sunt verificate automat, fără dependențe suplimentare. |
| Graficul grupurilor folosește golurile marcate și primite pe meci (varianta A), nu PCA | Axele au un înțeles direct și nu se adaugă o metodă nouă; limitarea (o treime dintre echipe apar mai aproape de alt centru) este documentată. |
| Figurile sunt construite cu `matplotlib.figure.Figure`, fără `pyplot` | Nu există stare globală; aceeași figură poate fi afișată în aplicație sau salvată. |
| Graficul Elo arată ratingul dinaintea fiecărui meci | Sunt exact valorile folosite de predicții, calculate doar din meciurile anterioare. |
| Un jurnal care nu poate fi citit este semnalat direct în ecran, cu butonul de backtest vizibil | Jurnalul poate fi reconstruit din aplicație, iar o fereastră de dialog s-ar fi repetat la fiecare schimbare de filă. |
| Numele echipelor de pe graficul grupurilor sunt așezate automat, fără o bibliotecă nouă, și din nou la fiecare redimensionare | Suprapunerile dispar aproape toate (o pereche în 99 de sezoane ale celor cinci ligi la mărimea implicită, niciuna la mărimea din fereastra aplicației; secțiunea 11.4), iar graficul rămâne determinist. |
| Testele de la un capăt la altul folosesc doar datele sintetice | Testele nu citesc baza de date reală; verificarea pe datele reale este o rulare separată, documentată în secțiunea 11.3. |
| PyInstaller în locul lui `pyside6-deploy` (Nuitka) | Construire simplă și rapidă, fără compilator C; funcționează bine cu PySide6, matplotlib și pandas. |
| Baza de date și jurnalul predicțiilor sunt incluse în pachet | Aplicația pornește gata de folosit, fără Python și fără să ruleze backtestul. |
| Aplicația împachetată scrie doar în folderul utilizatorului | Pachetul rămâne nemodificat; jurnalul reconstruit de utilizator este păstrat. |
| Pachetul pentru Windows se construiește cu GitHub Actions | Nu este nevoie de un calculator cu Windows, iar testele rulează și pe Windows. |
| Pachete nesemnate: `.dmg` pentru macOS și `.zip` pentru Windows | Semnarea costă; avertismentele de la prima deschidere sunt explicate în `README.md`. |
| Opțiunea `--self-test` | Singura verificare automată a unui pachet; o folosește și fluxul pentru Windows. |
| Cinci ligi, aceleași 20 de sezoane și aceeași sursă | Comparația dintre ligi folosește date de același fel și aceleași perioade. |
| Fiecare ligă este calibrată pe propriile sezoane de calibrare, cu aceleași grile | Avantajul terenului propriu, golurile și egalurile diferă între ligi; aceeași regulă pentru toate evită alegerea după rezultate. |
| Ferestrele de „un sezon” urmează mărimea obișnuită a ligii | O fereastră de 380 de meciuri ar acoperi mai mult de un sezon într-o ligă cu 18 echipe. |
| Grila lui $N$ merge până la cinci sezoane pentru toate ligile | Două ligi își alegeau marginea grilei; aceeași grilă pentru toate a schimbat și valoarea La Liga (38 → 76). |
| Sezonul Ligue 1 2019/20, oprit oficial, este păstrat ca excepție documentată | Meciurile jucate sunt reale; eliminarea lor ar rupe istoricul echipelor. |
| K-Means sare peste sezoanele fără statistici de șuturi | Profilul unei echipe are nevoie de șuturi; restul modelelor folosesc media ligii unde lipsesc. |
| Sigla PitchSense: monograma PS albă pe un pătrat rotunjit albastru–grena, fără alte elemente | Inițiale pe un pătrat, ca la aplicațiile de scoruri (LiveScore); o stemă de club încercată înainte semăna prea mult cu cea a Barcelonei, iar dintre trei variante ale monogramei (fără minge, cu silueta mingii, cu liniile terenului) echipa a ales-o pe cea minimalistă (`docs/brand.md`). |
| Temă întunecată cu blaugrana și un singur accent auriu | Aspectul site-urilor de fotbal pe care publicul le folosește (FC Barcelona, LiveScore, OneFootball); aurul arată pe fiecare ecran un singur lucru. |
| Barlow Condensed pentru titluri și cifre, Libre Franklin pentru text, ambele incluse în aplicație | O literă condensată de sport pentru ce se citește dintr-o privire și una clasică de ziar pentru text; aceleași pe macOS, pe Windows și în grafice, cu diacriticele românești; licențele permit includerea. |
| Stilul Qt Fusion, o paletă Qt întunecată și o singură foaie de stil | Aplicația arată la fel pe ambele sisteme și oricare ar fi tema sistemului. |
| Bara de sus cu ecranele și panoul ligilor în stânga, ca la LiveScore | Ecranele și ligile se aleg cu un singur clic, iar liga aleasă se vede mereu. |
| Sigla, steagurile și ecusoanele sunt desenate cu QPainter, literele din cercuri și dreptunghiuri, nu cu un font | Desenul este exact la fel pe orice sistem și se poate testa, atât geometric, cât și citind culorile pixelilor. |
| Echipele au ecusoane cu trei litere, ligile steagul țării | Stemele cluburilor și siglele ligilor sunt mărci înregistrate și nu fac parte din date. |
| Serviciile unei ligi sunt deschise la prima alegere și păstrate | Pornirea nu așteaptă cele cinci ligi; schimbarea ligii este imediată după prima dată. |
| Alegerile utilizatorului (liga, echipa) sunt într-un fișier JSON în folderul utilizatorului | Pachetul rămâne nemodificat; un fișier deteriorat sau imposibil de scris nu oprește aplicația. |
| Textul afișat este tradus într-un singur loc (`formatting.py`, `labels.py`) | Jurnalele, testele și codul păstrează identificatorii în engleză; afișarea românească este consecventă. |
| Cardul Acasă spune dacă avantajul modelului cu cel mai mic scor Brier este real | Un clasament după diferențe de 0,0001 ar sugera un câștigător acolo unde nu există unul. |
| Versiunea este scrisă doar în `app/__init__.py` | Pachetele, `pyproject.toml` și fereastra arată mereu aceeași versiune. |
| Iconițele pachetelor (`.icns`, `.ico`) sunt scrise de noi, cu imagini PNG desenate din siglă | Iconița urmează mereu sigla și nu este nevoie de o bibliotecă de imagini nouă. |
| Un fișier `VERSION` în folderul jurnalelor; o actualizare înlocuiește jurnalele vechi | Jurnalele calculate de modele mai vechi nu mai pot ajunge în aplicația nouă; în aceeași versiune, jurnalele reconstruite rămân. |
