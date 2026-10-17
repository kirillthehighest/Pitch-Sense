# Arhitectura aplicației PitchSense

Acest document descrie structura aplicației, fluxul datelor și deciziile tehnice luate până acum (fazele 0–21). Se actualizează ori de câte ori structura se schimbă.

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
| `tools/` | Unelte folosite o dată, în afara aplicației: stemele cluburilor (`crests.py`), descărcate în `app/ui/assets/` (Faza 19). | aplicația și internetul |

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
| `live.py`, `update.py` | Sezonul în desfășurare: descărcarea, verificarea, potrivirea numelor echipelor și citirea meciurilor programate (`Fixture` în `models.py`); comanda `python -m app.data.update` (secțiunea 15). |
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

### 12.8. Versiunea 0.3.0 (Faza 20)

Pachetele versiunii 0.3.0 conțin tot ce au adus fazele 18 și 19: sezonul în desfășurare, cu meciurile programate și predicțiile lor, butonul „Actualizează datele”, cele patru ecrane noi, stemele cluburilor și imaginile ligilor. Față de 0.2.0:

- **Versiunea** devine 0.3.0 în `app/__init__.py`. La prima pornire, jurnalele 0.2.0 din folderul utilizatorului sunt înlocuite, după regula din secțiunea 12.7.
- **Conținutul pachetului** are în plus instantaneul sezonului în desfășurare, descărcat la construire (`data/live`), stemele (`app/ui/assets/crests/`) și imaginile ligilor (`app/ui/assets/leagues/`). Instantaneul este copiat în folderul utilizatorului doar dacă e mai nou decât ce are acolo (secțiunea 15.2).
- **Opțiunea `--update`** (`python -m app --update` sau aplicația împachetată) face aceeași actualizare ca butonul, fără fereastră, și se termină cu codul 0 dacă a reușit. Ea face actualizarea din pachet verificabilă automat, pe ambele sisteme. Fluxul pentru Windows o rulează înaintea autoverificării și arată începutul fișierului `update.json` scris în folderul utilizatorului.

Verificare (2026-10-15):

- **macOS** (Mac cu Apple Silicon): `python packaging/build.py` a construit pachetul.
  - Mărimea: imaginea `.dmg` are 79 MB, aplicația despachetată 168 MB.
  - Autoverificarea a trecut, 23 din 23, atât din `dist/`, cât și din imaginea `.dmg` montată doar pentru citire.
  - Folderul utilizatorului de pe Mac-ul de test avea jurnalele și `VERSION` ale lui 0.2.0 și un instantaneu al sezonului mai vechi decât cel din pachet. Prima pornire a lui 0.3.0 a înlocuit jurnalele, a scris `VERSION` 0.3.0 și a copiat instantaneul nou.
  - `PitchSense --update`, rulat din pachet, a descărcat sezonul 2026/27 cu certificatele sistemului: 60, 78, 60, 45 și 54 de meciuri jucate, 320, 302, 320, 261 și 252 programate. Este prima încercare a actualizării dintr-o aplicație împachetată; în Faza 18 fusese încercată doar din codul sursă.
- **Windows** (fluxul „Windows package”, ramura `phase-20`): toate cele 771 de teste și verificarea codului au trecut, pachetul `.zip` are 93 MB, `PitchSense.exe --update` a descărcat sezonul 2026/27 în `%LOCALAPPDATA%\PitchSense\live`, iar autoverificarea pachetului a trecut (23 din 23).

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

Semnul, culorile, literele și regulile interfeței sunt descrise, cu motivele lor, în `docs/brand.md`. Această secțiune descrie structura din Faza 16; Faza 21 a înlocuit sigla, culorile și stilul (secțiunea 17).

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
  - Nu mai numește „cel mai bun model” doar după cel mai mic scor Brier: spune și dacă diferența față de următorul model este reală. În La Liga, de exemplu, Elo (0,5776) și regresia logistică (0,5777) nu difereau real (rularea din 2026-10-05).
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

## 15. Sezonul în desfășurare și meciurile care urmează (Faza 18)

Până în Faza 17, aplicația prezicea meciuri deja jucate (pentru evaluare) și meciuri ipotetice. Datele istorice servesc statisticilor și calibrării; o predicție are sens pentru un meci care nu s-a jucat încă. Faza 18 adaugă sezonul în desfășurare: rezultatele de până acum și meciurile programate, prezise de cele trei modele.

### 15.1. Sursele

| Ce | Sursa | Fișierul păstrat |
|---|---|---|
| Rezultatele sezonului de până acum | Football-Data.co.uk, aceeași sursă și același format ca `data/raw` (`https://www.football-data.co.uk/mmz4281/2627/<cod>.csv`) | `<cod>.csv` |
| Calendarul întregului sezon | openfootball/football.json, domeniu public (CC0 1.0): `https://raw.githubusercontent.com/openfootball/football.json/master/2026-27/<fișier>.json`, cu fișierele `en.1`, `es.1`, `it.1`, `de.1`, `fr.1` (câmpul `calendar` din `competitions.py`) | `<cod>.json` |
| Descrierea descărcării | scrisă de aplicație: sezonul, ora (UTC), adresa și amprenta SHA-256 a fiecărui fișier, versiunea aplicației | `update.json` |

Rezultatele vin doar de la Football-Data. Calendarul primește scorurile mai târziu (pe 15.10.2026, ultimul scor din calendar era din 20.09.2026, iar Football-Data avea meciurile până pe 12.10.2026), așa că din el se folosesc doar meciurile nejucate. Fișierele sunt păstrate nemodificate în `data/live/`, care nu este inclus în git, ca baza de date.

### 15.2. Actualizarea

- Butonul **Actualizează datele** din bara de sus sau comanda `python -m app.data.update`. Este singurul acces la internet al aplicației și are loc doar la cererea utilizatorului; fără el, aplicația funcționează cu ultimele date descărcate.
- Sezonul este dedus din data zilei: sezoanele încep la 1 iulie (`season_of` în `preprocessing.py`).
- Fișierele sunt descărcate într-un folder temporar și verificate:
  - rezultatele, cu aceleași reguli ca fișierele brute (coloane, date, scoruri, duplicate);
  - în plus, sezonul trebuie să poată deveni un tur-retur complet: cel mult $t$ echipe, nicio echipă cu mai mult de $2(t-1)$ meciuri, nicio gazdă care primește de două ori aceeași echipă (`in_progress_season_problems`);
  - calendarul: JSON valid, toate datele în fereastra sezonului, nicio pereche gazdă–oaspete de două ori.

  Doar după toate verificările, folderul nou îl înlocuiește pe cel vechi. O descărcare eșuată sau un fișier deteriorat lasă datele anterioare neschimbate, iar fereastra spune ce s-a întâmplat.
- Conexiunea este HTTPS, verificată cu certificatele sistemului. Python de pe python.org nu are certificate proprii pe macOS, așa că aplicația le citește din `/etc/ssl/cert.pem`; pe Windows, Python folosește depozitul sistemului. Nu a fost nevoie de o bibliotecă nouă.
- Un fișier mai mare de 5 MB este refuzat (un sezon are circa 0,2 MB). Un fișier care nu există încă (HTTP 404, vara, înainte de noul sezon) este explicat ca atare.
- Dintr-un pachet de instalare, descărcarea se face în folderul utilizatorului (`~/Library/Application Support/PitchSense/live`, `%LOCALAPPDATA%\PitchSense\live`). Pachetul livrează instantaneul de la construcție, copiat la pornire doar dacă este mai nou decât ce are utilizatorul (`copy_bundled_live`).

### 15.3. Potrivirea numelor echipelor

Cele două surse scriu numele diferit („Club Atlético de Madrid” și „Ath Madrid”, „RC Deportivo La Coruña” și „La Coruna”). Potrivirea nu este un tabel scris de mână, ci este dedusă din date (`match_team_names`):

1. Fiecare meci cu scor din calendar este pus în pereche cu meciul Football-Data din aceeași zi și cu același scor (sau din ziua de dinainte ori de după, dacă sursele nu au aceeași dată), dar doar dacă există exact un astfel de meci.
2. Fiecare pereche este un vot pentru două potriviri: gazdele între ele și oaspeții între ei.
3. Un nume din calendar primește numele Football-Data cu cel puțin 2 voturi și cel puțin 75% din voturile lui. Două nume din calendar nu pot primi același nume.

O echipă care nu poate fi potrivită sigur este raportată, iar meciurile ei programate sunt lăsate deoparte: nu sunt ghicite. Pe 15.10.2026, toate cele 96 de echipe ale celor cinci ligi au fost potrivite.

### 15.4. Predicția meciurilor programate

`predict_season` (`app/prediction/prediction_engine.py`) prezice, într-o singură rulare, toate meciurile jucate (exact ca `predict_history`) și toate meciurile programate. Fiecare meci programat intră ca meci înlocuitor (scor 0–0, nefolosit), datat **în ziua de după ultimul meci jucat** (`as_of`); data reală rămâne pentru afișare.

- Niciun model nu folosește rezultatele zilei pe care o prezice, iar după `as_of` nu mai urmează nimic. Astfel, scorul inventat al unui înlocuitor nu ajunge în nicio predicție, iar un meci programat primește aceleași probabilități ca atunci când este prezis singur (testat). Pe macOS valorile sunt identice. Pe Windows, probabilitățile regresiei logistice pot diferi la ultima zecimală (circa 1e-16), pentru că meciurile unei zile trec printr-un singur produs de matrice, iar biblioteca de calcul adună altfel termenii când numărul de meciuri diferă; testele compară aceste cazuri cu o toleranță de 1e-12.
- Un înlocuitor pus la data lui reală ar fi intrat, cu scorul inventat, în istoricul meciurilor programate de după el. Toate meciurile programate sunt prezise din tot ce se știe azi: nimic mai nou nu este cunoscut.
- Meciurile jucate își păstrează exact predicțiile din `predict_history` (testat; pe datele reale, toate cele 7.678 de meciuri ale La Liga au aceleași probabilități).
- Regresia logistică și modelul egalurilor din Elo folosesc ultima reantrenare de luni de dinainte de `as_of`, pe meciurile de dinaintea acelei zile de luni, ca în backtest.
- Un meci programat trebuie să fie din sezonul ultimului meci jucat, între echipe care au jucat în acest sezon, și să nu repete un meci jucat sau alt meci programat.
- Un meci cu data din calendar trecută, dar fără rezultat (amânat sau încă neînregistrat; pe 15.10.2026: Vallecano – Ath Bilbao, programat pe 10.10.2026) este prezis la fel și marcat pe ecran.
- O ligă cu meciurile ei programate se prezice în același timp ca istoricul (circa 7 s).
- În modul „Orice meci”, o dată de după ultimul meci jucat al sezonului în desfășurare folosește tot ziua `as_of`, pentru că informația este aceeași. O pereche programată primește exact predicția din lista meciurilor programate.

### 15.5. Serviciile și ecranele

- `DataCatalog.load(..., live_dir)` adaugă sezonul în desfășurare la sezoanele din baza de date, dacă este mai nou decât ultimul dintre ele și are meciuri jucate: `fixtures`, `current_season`, `updated_at`, `unmatched_teams`. Fișierele deteriorate nu împiedică deschiderea ligii: sunt arătate sezoanele încheiate, iar `live_problem` spune ce nu a mers (fereastra îl arată o dată).
- `PredictionService(matches, fixtures)` prezice ambele în `prepare`; `upcoming()` întoarce meciurile programate, iar `predict` răspunde din memorie pentru un meci programat.
- `TeamService(..., in_progress=...)`: sezonul în desfășurare nu este niciodată „încheiat”, deci nu are profil și grup al sezonului. Grupurile K-Means descriptive sunt calculate doar pe sezoanele încheiate, cu aceleași rezultate ca înainte; grupul de dinaintea sezonului se calculează ca pentru orice sezon.
- **Predicție**: modul „Programat” (ales din start când există meciuri programate) arată data, ora locală și ce meciuri folosește predicția; „Jucat” și „Orice meci” au rămas. **Echipe**: clasamentul sezonului în desfășurare de până acum. Panoul din stânga arată sursele și ora ultimei actualizări.
- **Evaluarea nu se schimbă.** Backtestul, jurnalele, calibrările și comparațiile folosesc doar sezoanele încheiate din baza de date. Sezonul în desfășurare nu face parte din evaluarea raportată.

### 15.6. Verificare

Rulări din 2026-10-15:

- **Teste.** Toate cele 744 de teste trec; `ruff check` și `ruff format --check` nu găsesc nimic. Teste noi:
  - `tests/test_live.py`: calendarul, potrivirea numelor, descărcarea printr-o sursă falsă, înlocuirea folderului doar după verificare, păstrarea datelor la o eroare, copierea instantaneului și comanda;
  - verificările sezonului în desfășurare, `Fixture` și `calendar`;
  - `predict_season`: istoricul neschimbat, meciurile programate care nu se influențează între ele, egalitatea cu `predict_fixture` la `as_of`, un rezultat jucat care schimbă meciurile de după el, meciurile programate invalide;
  - serviciile, ecranele (butonul de actualizare reușit și eșuat, datele deteriorate), testul de la un capăt la altul (fișiere brute → bază de date → descărcare → fereastră, cu aceleași cifre ca motorul) și autoverificarea.

  Testele nu folosesc rețeaua.
- **Pe datele reale**, actualizarea din 15.10.2026:

  | Liga | Echipe | Meciuri jucate | Meciuri programate | Total |
  |---|---|---|---|---|
  | Premier League | 20 | 60 | 320 | 380 |
  | La Liga | 20 | 78 | 302 | 380 |
  | Serie A | 20 | 60 | 320 | 380 |
  | Bundesliga | 18 | 45 | 261 | 306 |
  | Ligue 1 | 18 | 54 | 252 | 306 |

  Fiecare ligă are exact numărul de meciuri al unui sezon, iar toate echipele au fost potrivite.
- **Ecranele** Predicție și Echipe au fost desenate fără fereastră, cu datele reale, și verificate vizual.
- **Autoverificarea** pe datele reale: 21 din 21 (verificarea nouă: sezonul în desfășurare se citește fără erori; La Liga are 302 meciuri programate). Pentru graficul grupurilor, autoverificarea alege acum ultimul sezon încheiat, pentru că sezonul în desfășurare nu are grupuri. Aplicația pornește (`python -m app`) și rulează fără erori.
- **Pachete.** macOS: `python packaging/build.py` descarcă sezonul în timpul construcției; `.dmg` de 74 MB; autoverificarea din `dist/` trece 21 din 21, iar instantaneul sezonului este copiat în folderul utilizatorului la prima pornire. Windows (GitHub Actions): toate cele 745 de teste trec, descărcarea sezonului reușește cu certificatele sistemului, `.zip` de 89 MB, autoverificarea trece 21 din 21 (Premier League, 320 de meciuri programate). Actualizarea apăsată în fereastra unei aplicații împachetate nu a fost încercată pe internet; aceeași funcție de descărcare a rulat din comandă pe ambele sisteme.

### 15.7. Limitări

- Orele de începere sunt cele locale din calendar.
- La începutul sezonului, numele unei echipe poate fi potrivit abia după ce echipa a jucat două meciuri. Până atunci, meciurile ei programate lipsesc, iar aplicația spune de ce.
- După 1 iulie, actualizarea trece la sezonul nou. Ca sezonul încheiat să rămână în aplicație, fișierul lui trebuie adăugat în `data/raw/` și baza de date reconstruită (`python -m app.data.build_database`).
- O schimbare a calendarului (un meci mutat) apare doar după o actualizare.
- Clasamentele nu includ deducerile de puncte, ca până acum.

## 16. Interfața centrată pe meciuri (Faza 19)

Echipa a cerut o aplicație care pornește de la meciuri, ca LiveScore și OneFootball: ecranul Acasă, cu scorul Brier și rezultatele modelelor, nu spunea nimic utilizatorului, iar predicția unui meci deja jucat nu este o predicție. Meniul are acum patru ecrane, iar stemele cluburilor și fotografiile ligilor au intrat în aplicație.

### 16.1. Ecranele

| Ecran | Ce arată | Fișier |
|---|---|---|
| **Meciuri** (primul) | meciurile unei zile din toate ligile, grupate pe ligă, liga aleasă prima; banda de zile (șapte zile, săgeți de o săptămână), filtrul „Toate ligile / Doar liga”, modelul ales; pentru fiecare meci ora (sau „Final”, „Amânat”), stemele, scorul și cele trei probabilități ale modelului ales, cu cea mai mare colorată; la un meci jucat, o bifă verde sau o cruce roșie spune dacă rezultatul cel mai probabil s-a întâmplat. În dreapta: echipa ta (forma, următorul meci, ultimul rezultat) și începutul clasamentului. Se deschide pe prima zi cu meciuri de azi înainte. | `app/ui/matches.py`, `match_widgets.py` |
| **Pagina meciului** (clic pe un meci) | cardul albastru–grena cu stemele mari, scorul sau „VS” și starea (Programat, Final, Amânat, Meci ipotetic); barele celor trei modele, fiecare cu o frază simplă despre ce folosește; rezultatul și ce modele l-au anticipat; ce meciuri au folosit predicțiile; cum vin echipele (loc, puncte, ultimele cinci rezultate, ratingul Elo, la ziua predicției); scorurile probabile și harta lor (Poisson). „Alt meci…” deschide aceeași pagină pentru oricare două echipe ale unui sezon, la o dată aleasă. | `app/ui/match_detail.py` |
| **Clasament** | clasamentul unui sezon (până acum, pentru sezonul în desfășurare) sau la o dată, cu stemele și ultimele cinci rezultate; un clic pe o echipă îi deschide pagina, în acel sezon | `app/ui/standings.py` |
| **Echipe** | pagina unei echipe, ca pe site-urile canalelor sportive: stema și numele cu litere mari pe o bandă albastru–grena, șase cifre (loc, meciuri, victorii, goluri marcate și primite, puncte), forma, acasă și în deplasare, următorul meci și ultimele cinci rezultate (cu predicțiile), profilul K-Means explicat în cuvinte, ratingul Elo și grupurile | `app/ui/team_page.py` |
| **Analiză** | file: Cum funcționează (fiecare algoritm și măsurile, pe înțelesul oricui), Sezonul curent (cum au prezis modelele meciurile jucate ale sezonului în desfășurare), Modele (fostul ecran Modele), Ligi (fostul ecran Ligi), Surse (datele, stemele, fotografiile și literele, cu licențele) | `app/ui/analysis.py` |

Ecranele Acasă, Predicție și vechiul Echipe au fost scoase (`home.py`, `match_prediction.py`, `team_analysis.py`); tot ce arătau există în ecranele noi. Scorul Brier și rezultatele evaluării stau doar în Analiză.

### 16.2. Modelul din listă

Lista meciurilor arată probabilitățile unui singur model, ca să rămână ușor de citit; pagina meciului le arată pe toate. Implicit este regresia logistică: pe toate cele cinci ligi la un loc ea are cel mai mic scor Brier, iar diferența față de Elo și Poisson este reală (`docs/leagues.md`, secțiunea 5). Utilizatorul poate alege oricare model. Nu este calculată o medie a modelelor: ar fi un al patrulea model, neevaluat.

### 16.3. Datele pentru ecrane

- `PredictionService` (`app/services/predictions.py`) păstrează, după `prepare`, meciurile fiecărei zile (`MatchForecast`: jucat sau programat, cu predicțiile tuturor modelelor) și răspunde la `match_days`, `on_day` și `team_matches` fără calcule noi. `season_check` scoate acuratețea, scorul Brier și pierderea logaritmică ale fiecărui model pe meciurile jucate ale unui sezon, cu funcțiile din `app/evaluation/metrics.py`. `forecast_of` aduce un meci ipotetic în aceeași formă.
- `TeamService.rating_before` dă ratingul Elo al unei echipe înaintea unei zile; `TeamService.form` dă ultimele cinci rezultate.
- Fereastra pregătește predicțiile tuturor ligilor în fundal, pe rând, liga aleasă prima (`MainWindow._prepare_next`). Până când o ligă este gata, grupul ei din Meciuri spune „Se pregătesc predicțiile…”. Pe calculatorul de dezvoltare, prima ligă este gata în circa 7 s, toate cinci în circa 40 s.
- Ziua de azi vine din `AppContext.today`, ca testele să o poată fixa.

### 16.4. Stemele cluburilor

Echipa a ales stemele reale, de pe Wikipedia, la rezoluție mică, păstrate doar în depozitul privat și în pachete, cu mențiunea că aparțin cluburilor.

- `tools/crests.py` caută articolul englezesc al fiecărui club: după numele complet din calendar, pentru echipele sezonului în desfășurare, altfel după numele Football-Data și țară. Primul rezultat descris ca „football club” este ales, iar opt nume fără un rezultat bun au articolul scris în unealtă (de exemplu `Sp Gijon` → Sporting de Gijón). Stema este imaginea principală a articolului sau, dacă API-ul nu o dă (Atalanta, Fiorentina, Inter, Man City), imaginea din caseta de informații.
- Stemele sunt micșorate la cel mult 128 px și salvate în `app/ui/assets/crests/<nume>.png` (3,2 MB pentru 209 echipe). `sources.json` păstrează, pentru fiecare, articolul și fișierul. Toate cele 209 de steme au fost verificate vizual pe o singură foaie (`--sheet`) și sunt ale cluburilor corecte.
- Unealta se prezintă serverelor Wikimedia cu numele și adresa proiectului, face o cerere pe secundă și reîncearcă după un răspuns „prea multe cereri” (HTTP 429).
- `team_badge` (`app/ui/brand.py`) desenează stema; o echipă fără stemă păstrează ecusonul cu trei litere. O stemă aproape în întregime întunecată (sub 10% din pixeli cu luminanța peste 0,25: Juventus, Tottenham, Derby, Swansea și alte șase) ar dispărea pe fundalul întunecat, așa că stă pe un disc deschis.
- Stemele sunt mărci ale cluburilor. Sunt folosite doar ca să recunoști echipele, într-un proiect universitar privat, iar ecranul Analiză → Surse spune asta.

### 16.5. Imaginile ligilor

Fiecare ligă are în antet o imagine cu jucătorii ei. La început erau fotografii libere de stadioane de pe Wikimedia Commons (Anfield, Camp Nou, San Siro, Signal Iduna Park, Parc des Princes, CC BY și CC BY-SA). După acceptarea fazei, echipa le-a înlocuit cu cinci imagini promoționale DAZN, alese de ea, și a cerut ca jucătorii să încapă în antet.

- Imaginile stau în `app/ui/assets/leagues/<cod>.jpg` (1,6 MB în total), nemodificate; echipa a schimbat apoi imaginea Bundesligii cu una cu Kane pe fond roșu. `sources.json` spune, pentru fiecare, sursa (DAZN) și unde începe fâșia arătată (`top`, ca parte din înălțimea imaginii, puțin deasupra celui mai înalt cap). Un decupaj dat ca procent din spațiul rămas tăia capetele în ferestrele late (Mbappé, Bruno Fernandes), pentru că acolo imaginea se mărește; marginea de sus fixată pe imagine le păstrează la orice lățime (verificat la 1192 și 1672 px).
- În Faza 19, antetul (`HeroBanner`) avea 236 px. Imaginea ocupa partea dreaptă, cel mult 58% din lățime și cel mult 760 px, ca o fereastră lată să nu taie capetele, și se estompa spre stânga în culoarea antetului. Faza 21 a refăcut antetul: imaginea la rezoluția ecranului, trecând în culoarea propriei margini (secțiunea 17.4). În colț scrie „Imagine: DAZN”.
- Drepturile asupra imaginilor, ale jucătorilor, siglelor și sponsorilor aparțin deținătorilor lor. Imaginile sunt folosite doar în depozitul privat și în pachete și nu se publică, iar Analiză → Surse spune asta. Unealta pentru fotografiile Commons (`tools/league_photos.py`) a fost scoasă.

### 16.6. Corecturi găsite pe parcurs

- **Tema reaplicată.** `apply_theme` reaplica foaia de stil întregii aplicații, iar Qt restiliza fiecare fereastră încă vie. În suita de teste, autoverificarea dura astfel 19 s în loc de 0,06 s. Acum o temă deja aplicată nu mai este pusă din nou.
- **Semnul de nimerit.** Primul desen al bifei folosea un argument pe care PySide6 nu îl acceptă, iar eroarea din desenare trecea neobservată. Un test care citește culorile pixelilor a prins-o.
- **Contrastul.** Zilele fără meciuri și cuvântul „Amânat” erau scrise cu culori prea slabe pentru text (sub 4,5 : 1); acum folosesc culoarea textului secundar. Faptul că o predicție a fost nimerită se vedea doar prin culoare; acum are și forma bifei sau a crucii.
- **Deschiderea unei echipe din clasament.** Un clic pe o echipă din clasamentul 2006/07 deschidea pagina ei din cel mai recent sezon; acum o deschide în sezonul clasamentului.
- **După actualizare**, ecranul Meciuri rămânea pe ziua de dinainte; acum trece la următoarea zi cu meciuri din datele noi.

### 16.7. Verificare

Rulări din 2026-10-15:

- **Teste.** Toate cele 767 de teste trec; `ruff check` și `ruff format --check` nu găsesc nimic. Testele interfeței (`tests/test_ui.py`), cele de la un capăt la altul și cele ale autoverificării au fost mutate pe ecranele noi și verifică aceleași lucruri ca înainte: predicțiile unui meci jucat sunt cele din jurnal, clasamentul coincide cu fișierele brute, un meci ipotetic folosește doar meciurile dinaintea lui, un jurnal deteriorat este explicat pe loc. Teste noi:
  - banda de zile, modelul ales, filtrul ligilor, pagina meciului și a echipei, clasamentul cu formă;
  - bifa și crucea, citite din pixeli;
  - stemele și discul stemelor întunecate, fotografia din antet;
  - fila Sezonul curent și serviciile `on_day`, `team_matches`, `season_check` și `rating_before`.
- **Autoverificarea** pe datele reale: 23 din 23. Noile verificări: stemele și fotografia ligii sunt în aplicație, predicțiile tuturor celor cinci ligi, lista meciurilor și pagina unui meci, clasamentul și pagina echipei. Aplicația pornește (`python -m app`) și rulează fără erori.
- **Verificare vizuală.** Toate ecranele și filele au fost desenate cu datele reale, la 1440 × 960, și verificate: Meciuri (zi viitoare și zi jucată), pagina meciului, Clasament, Echipe, cele cinci file ale Analizei și antetul fiecărei ligi.
- **Pachete.** macOS: `.dmg` de 80 MB (stemele și fotografiile adaugă circa 6 MB), autoverificarea din `dist/` trece 23 din 23. Windows (GitHub Actions): toate cele 767 de teste trec, `.zip` de 94 MB, autoverificarea trece 23 din 23 (Premier League, 320 de meciuri programate).

### 16.8. Limitări

- Stemele sunt o fotografie a lor din 15.10.2026. Un club care își schimbă stema o păstrează pe cea veche până la o nouă rulare a uneltei.
- Pregătirea tuturor ligilor durează circa 40 s după pornire. Ecranul Meciuri arată ligile pe măsură ce sunt gata.
- Lista meciurilor arată un singur model odată.
- Grupurile K-Means apar doar pentru sezoanele încheiate, ca până acum.

## 17. Designul refăcut: culorile ligilor, sigla nouă, o fereastră de orice lățime (Faza 21)

Echipa a cerut să lucrăm mai mult la design. Așezarea ecranelor din Faza 19 a rămas. S-au schimbat:

- stilul;
- culorile, care urmează liga afișată și se schimbă cu o animație;
- sigla;
- antetul cu imaginea ligii;
- fereastra, care se potrivește oricărei lățimi.

Regulile vizuale și motivele lor sunt în `docs/brand.md`.

**Cele două versiuni.** Faza a avut două versiuni. Prima („sticlă întunecată”) a fost respinsă de echipă: animația sacada, imaginile își pierduseră calitatea, culorile păreau toxice, iar designul părea făcut în grabă. A doua, cea descrisă aici, a refăcut stilul după referințele echipei și a corectat cauzele tehnice (secțiunile 17.2 și 17.4).

### 17.1. Paletele ligilor

- `app/ui/themes.py` definește clasa `Theme`. Suprafețele și textul sunt aceleași pentru toate ligile: o noapte neutră, aproape neagră. Fiecare ligă are:
  - accentul, cu textul de pe el;
  - accentul scris pe întuneric;
  - culoarea adâncă a ligii.

  `theme_for(code)` dă paleta unei ligi; o ligă fără paletă primește paleta La Ligii (`DEFAULT_THEME`).
- **Paleta afișată.** `current_theme()` dă paleta de pe ecran. Piesele desenate o citesc de fiecare dată când se desenează, deci nu păstrează culori vechi.
- **Foaia de stil și paleta Qt.** `style_sheet(theme)` și `qt_palette(theme)` din `app/ui/theme.py` le generează din paleta unei ligi.
  - `apply_theme` le pune pe toată aplicația, la pornire și în autoverificare.
  - `apply_window_theme` le pune doar pe fereastră, la schimbarea ligii. Foaia ferestrei are întâietate față de cea a aplicației, iar restilizarea doar a ferestrei durează 0,15–0,3 s, față de 0,6–0,8 s pentru toată aplicația.
- **De ce nu doar paleta Qt.** O foaie de stil care citește culorile din paleta Qt (`palette(highlight)`) nu urmează o paletă schimbată ulterior; s-a încercat și nu funcționează. De aceea foaia se generează din nou.
- **Ce nu se schimbă.** Culorile formei și ale modelelor rămân în `app/visualization/palette.py`, aceleași pentru toate ligile. Barele de probabilitate folosesc accentul ligii pentru victoria gazdelor și două griuri pentru egal și pentru victoria oaspeților (`ProbabilityBars.colours`).
- **Graficele.** Graficele rămân construite fără Qt, în `app/visualization/charts.py`, cu Plus Jakarta Sans pentru text. `ChartView` le face transparente și înlocuiește, cu `on_surface`:
  - culoarea cardului (inelele marcajelor, spațiile dintre celule) cu cardul ligii;
  - auriul evidențierii cu accentul ligii.

  Un grafic de pe un ecran ascuns este recolorat imediat, dar redesenat abia când e arătat.

### 17.2. Schimbarea ligii

`MainWindow.show_league` face următoarele:

1. Dacă fereastra e pe ecran și liga are alte culori, păstrează o imagine a ei (`_snapshot`); o animație încă în curs e încheiată.
2. Pune foaia de stil și paleta noii ligi pe fereastră și îi schimbă iconița (`_restyle`).
3. Ecranul afișat își schimbă conținutul. Ecranele ascunse îl schimbă după animație (`_after_reveal`) sau în momentul în care sunt deschise, ca să nu întârzie animația.
4. După ce Qt livrează evenimentele amânate, păstrează o imagine a ferestrei noi. Aceste evenimente arată și așază rândurile noi; fără ele, imaginea ar fi prins fereastra fără rânduri.
5. `ThemeReveal` (`app/ui/transition.py`) arată imaginea veche și deschide în ea un cerc spre imaginea nouă, din colțul din stânga sus, în 0,8 s (`QVariantAnimation`, mișcare `OutCubic`).

**Marginea cercului.** Marginea are valuri, ca la Material You:

- `wave_edge` dă punctele marginii, la câte 8 px de-a lungul ei, calculate toate odată cu NumPy, o singură dată pe cadru;
- `wave_offset` adună două valuri sinusoidale, de 120 px și de 68 px, care se mișcă în sensuri opuse;
- `wave_amplitude` le scade înălțimea de la 18 la 4 px pe măsură ce cercul crește.

**Desenul unui cadru.** Stratul animației e opac (`WA_OpaquePaintEvent`) și desenează doar:

- imaginea nouă;
- imaginea veche, umplând partea încă acoperită (`cover`, un singur poligon) cu un pensul făcut din imagine, fără mască de tăiere;
- linia valului și două unde.

Un cadru redesenează doar banda prin care a trecut marginea de la cadrul precedent (`band`: fâșii de 16 px între două cercuri), nu toată fereastra.

**De ce sacada animația.** Au fost două cauze, găsite una după alta.

1. **Stratul transparent.** În prima versiune, stratul era transparent, așa că pentru fiecare cadru Qt redesena toată fereastra de sub el: carduri, rânduri, imaginea antetului, grafice.
2. **Calculul în fundal.** Și după ce stratul a devenit opac, echipa a văzut animația sacadând în aplicația reală. Măsurătorile din fereastra desenată fără ecran nu prinseseră cauza, pentru că acolo predicțiile erau gata. În aplicația reală, după pornire se calculează predicțiile celor cinci ligi, aproximativ 7,5 s fiecare. Calculul rula pe un fir de execuție al aceluiași proces, deci împărțea interpretorul Python cu fereastra. Fereastra aștepta după el la fiecare apel spre Qt.

   Măsurat la rezoluția Retina, cu o ligă în calcul:
   - schimbarea ligii bloca fereastra 4,8 s;
   - animația avea 11 cadre, la până la 270 ms unul de altul;
   - scurtarea intervalului de comutare al interpretorului (`sys.setswitchinterval`) a ajutat puțin (1,8 s, 10 cadre).

**Calculul în alt proces.** Acum predicțiile se calculează în alt proces (secțiunea 17.6), iar ecranele ascunse se schimbă după animație. În aceleași condiții:

- 50 de cadre, la cel mult 17,6 ms unul de altul, adică 60 pe secundă;
- un cadru se desenează în aproximativ 4 ms;
- fereastra se blochează 0,5 s înaintea animației la prima deschidere a unei ligi și aproximativ 0,3 s după aceea.

**Comportamentul.** Stratul lasă clicurile să treacă. O fereastră care nu este pe ecran se schimbă fără animație, la fel și una cu `animate = False`. Predicțiile unei ligi care sosesc în timpul animației se instalează după ea, ca transferul lor (aproximativ 0,14 s) să nu se vadă ca un salt.

### 17.3. Stilul și sigla

- **Suprafețele.** Fundalul ferestrei (`Backdrop`) e plat. Peste el stau:
  - cardurile plate, cu colțurile de 20 px și o margine albă la 6%;
  - navigarea, filtrele, jetoanele și sub-filele, ca pastile;
  - butoanele, cu colțurile de 12 px.
- **Literele.** Plus Jakarta Sans (SIL Open Font License 1.1, cinci grosimi statice, din depozitul autorilor) a înlocuit Libre Franklin; fișierele Libre Franklin au fost scoase. Textul nu mai e scris cu majuscule; Barlow Condensed a rămas pentru titlul ecranului, scoruri, cifre și numele echipelor pe pagina unui meci.
- **Rândurile de meci** (`MatchRow`), ca în Sportia:
  - ora sau „Final”;
  - gazdele cu stema în stânga, scorul sau „vs” pe o pastilă în mijloc, oaspeții cu stema în dreapta;
  - cele trei probabilități; cea mai mare e plină cu accentul.

  `MatchRow.chip_box` dă locul fiecărei probabilități; după el sunt așezate și capetele coloanelor (`ProbabilityHeading`). Un rând îngust pune gazdele și oaspeții pe două rânduri, cu scorul lângă ele, ca numele să nu fie tăiate.
- **Cardurile de ligă din Meciuri** (`LeagueGroup`) sunt desenate: steagul, liga, țara și numărul de meciuri, capetele coloanelor, apoi rândurile într-un chenar interior rotunjit.
- **Capetele meciului și echipei** folosesc `paint_head_card`: cardul luminat de sus de culoarea adâncă a ligii. Capul unui meci ia culoarea ligii meciului, chiar dacă e afișată altă ligă.
- **Sigla.** `logo_parts` din `app/ui/brand.py` ia conturul literelor „PS” din fontul Kanit Black Italic și unește contururile care se suprapun. Le potrivește în dreptunghiul dat și le taie cu o bandă înclinată la 15°. Rezultă două forme, desenate în alb și în accentul ligii.
- **Iconița.** Iconița pune sigla pe un pătrat aproape negru, luminat de culoarea adâncă a ligii. `packaging/icons.py` desenează iconițele pachetelor în culorile La Ligii și se oprește dacă fontul Kanit nu se încarcă.

### 17.4. Antetul cu imaginea ligii

`HeroBanner` umple tot antetul fără inteligență artificială:

1. **Imaginea.** Se desenează direct pe ecran, cu `drawImage`, la rezoluția lui: cel mult 62% din lățime și 860 px, ancorată în dreapta și tăiată de sus după `sources.json`.
2. **Fondul.** `edge_colour` dă culoarea medie a marginii stângi a fâșiei arătate (3% din lățime), întunecată cu 30%, și o păstrează după cheia imaginii. Amestecată pe jumătate cu culoarea adâncă a ligii, ea este fondul antetului.
3. **Trecerea.** Pe 50% din lățimea imaginii, de la marginea ei, un gradient trece din fond în transparent, începând cu un pixel înaintea imaginii, ca nicio coloană să nu rămână neacoperită.
4. **Explicația.** Lățimea explicației se recalculează după lățimea imaginii, ca textul să rămână la stânga ei.

**De ce se pierdea calitatea în prima versiune.** Imaginea clară era pregătită într-o `QImage` de mărimea antetului în puncte, fără densitatea ecranului. Pe Retina se desena deci la jumătate din rezoluție, peste o copie estompată. Ambele au fost scoase.

### 17.5. O fereastră de orice lățime

În Faza 19, la lățimi mai mici, coloana din dreapta a ecranului Meciuri era tăiată, iar Echipe și Ligi aveau bară de derulare orizontală. Lățimea minimă a ferestrei era 1180 px; acum este 1024 px.

- **`ResponsiveBox`** pune piesele alături sau, sub un prag de lățime, una sub alta:
  - piesele cu lățime fixă (coloana „Echipa ta”, 340 px) iau atunci toată lățimea;
  - așezarea nu impune lățimea tuturor pieselor la un loc, altfel cutia n-ar putea deveni destul de îngustă ca să le pună una sub alta.
- **`ReflowGrid`** așază piesele pe atâtea coloane câte încap: cele șase cifre ale echipei, cele cinci carduri de ligă.
- **`MatchRow`** trece singur pe două rânduri sub 600 px.
- **`MainWindow.fit_width`** păstrează doar steagurile în panoul ligilor sub 1280 px și doar semnul siglei sub 1180 px.
- **Clasamentul.** Celulele tabelului nu mai au spațiu interior, ca pătrățelele de formă să încapă întregi în coloana lor.

Pragurile fiecărui ecran sunt în `docs/brand.md`, secțiunea 5.5.

### 17.6. Predicțiile, în alt proces

`PredictionService` are pasul lent despărțit în două:

- `preparation` dă calculul ca o sarcină care poate rula în alt proces: o funcție de modul (`compute_predictions`) cu argumente care sunt doar date;
- `install` primește rezultatul (`PreparedPredictions`).

`prepare` le face pe amândouă pe loc, ca înainte.

`compute_in_process` (`app/ui/worker.py`) trimite sarcina unui singur proces de lucru, pornit o dată, cu metoda `spawn`, și o așteaptă dintr-un fir de execuție. Rezultatul se întoarce ca șir de octeți (`pickle`), aproximativ 30 MB pentru o ligă, iar fereastra îl despachetează când vrea. `AppContext.compute` alege unde se face calculul: testele folosesc `compute_here`, în același proces. La închiderea ferestrei, `stop_processes` oprește procesul de lucru fără să aștepte calculul în curs.

Într-un pachet, procesul de lucru pornește din nou programul. `multiprocessing.freeze_support()` din `app/__main__.py` îl transformă în proces de lucru înainte să ruleze altceva. Autoverificarea pachetelor încearcă și acest drum, pentru că își pregătește predicțiile prin `context.compute`.

### 17.7. Ce trece în Etapa 22

După a doua versiune, echipa a mai cerut:

- pe pagina echipei: cardul formei aranjat aliniat, iar cardul K-Means redenumit „Profilul echipei”, fără descriere;
- în Analiză: fără spațiul gol de sub grafice și cu coloanele tabelelor de lățimi măsurate;
- un layout cu o singură bară laterală (varianta A, aleasă de echipă dintre patru);
- un card „Meciul zilei” cu imaginea ligii;
- meciurile din sezoanele anterioare;
- un ecran cu predicțiile nimerite, ratate și surprizele;
- imagini cu stadioane și jucători.

Echipa a hotărât apoi ca interfața să fie refăcută pe web, peste serviciile Python, într-o etapă nouă (22). Aceste cereri intră acolo. Etapa 21 se încheie cu culorile ligilor, sigla, stilul, adaptarea la lățime și animația reparată.

### 17.8. Verificare

Rulări din 2026-10-15 și 2026-10-16:

- **Teste.** Toate cele 815 teste trec; `ruff check` și `ruff format --check` nu găsesc nimic. Fișiere de test noi:
  - `tests/test_themes.py`: suprafețele comune, accentele, contrastele tuturor textelor, inclusiv antetul cu imaginea reală a fiecărei ligi, barele de probabilitate și foaia de stil a fiecărei ligi;
  - `tests/test_transition.py`: cercul, valurile, partea acoperită, cele două imagini, stratul opac, încheierea animației.

  Celelalte teste:
  - `tests/test_brand.py` verifică noua siglă: tăietura, culorile în fiecare ligă, numele, varianta îngustă, iconița în culorile ligii, fonturile;
  - `tests/test_ui.py` verifică schimbarea culorilor ferestrei (cu și fără animație, inclusiv o schimbare întreruptă), fereastra îngustă, lipsa barei orizontale la 1024, 1280 și 1440 px, piesele adaptive, antetul și graficul ascuns;
  - `tests/test_charts.py` verifică trecerea unui grafic pe altă ligă;
  - `tests/test_icons.py` verifică culorile iconiței pachetelor;
  - `tests/test_worker.py` verifică faptul că o sarcină rulată în alt proces dă exact același rezultat;
  - `tests/test_services.py` verifică faptul că predicțiile calculate ca sarcină și instalate apoi sunt aceleași;
  - `tests/test_ui.py` verifică faptul că ecranele ascunse și predicțiile sosite în timpul animației urmează după ea.
- **Autoverificarea** are două verificări noi, culorile ligii și valul: 25 în total. Pe datele reale trece 25 din 25, iar aplicația pornește (`python -m app`) și rulează fără erori.
- **Verificare vizuală.** Ecranele au fost desenate cu datele reale, la rezoluția Retina (`QT_SCALE_FACTOR=2`), și verificate:
  - Meciuri în fiecare ligă;
  - pagina meciului, Clasament, Echipe și Analiză;
  - fereastra la 1100 și 1440 px;
  - animația în patru momente ale ei.

  Pe datele reale, niciun ecran nu se derulează în lateral la 1024, 1180, 1280, 1440 și 1920 px.
- **Pachete.** Versiunea a rămas 0.3.0; o versiune nouă cere o fază de lansare. În ambele pachete, autoverificarea își calculează predicțiile în procesul separat, deci încearcă și pornirea lui din pachet.
  - macOS: `.dmg` de 79 MB. Autoverificarea trece 25 din 25 din `dist/` și din imaginea `.dmg` montată doar pentru citire, fără procese rămase după ea.
  - Windows (GitHub Actions): toate cele 815 teste trec, `.zip` de 93 MB. Actualizarea cu `--update` din pachet reușește, iar autoverificarea trece 25 din 25.
- **Procesul separat.** Aplicația pornită din sursă își calculează predicțiile în procesul de lucru. Oprită forțat (`kill -9`), nu lasă procese în urmă: procesul de lucru se oprește singur când dispare fereastra.

### 17.9. Limitări

- Pachetele au iconița în culorile La Ligii: sistemul o citește din pachet înainte de pornire.
- Mesajele de la pornire (dinaintea ferestrei) și indiciile de la trecerea mausului au culorile La Ligii, pentru că nu aparțin ferestrei.
- Timpul unui cadru al animației a fost măsurat pe o fereastră desenată fără ecran, cu o ligă în calcul; pe ecranul real depinde și de sistem.
- Prima deschidere a unei ligi blochează fereastra aproximativ 0,5 s înaintea animației, cât își deschide datele.

## 18. Interfața web (Faza 22)

După Faza 21, echipa a hotărât ca ecranele să fie refăcute pe web, într-o fereastră de desktop, peste algoritmii și serviciile Python, care rămân neschimbate. Alegerile echipei din 2026-10-16: Tauri pentru fereastră (nu Electron), un server FastAPI local, grafice desenate în interfață (Recharts), Node și Rust instalate cu Homebrew. La acceptarea etapei, echipa a cerut ca interfața veche (PySide6) să fie scoasă (secțiunea 18.9).

### 18.1. Straturile

```
fereastra (Tauri, Rust: web/src-tauri)
  └─ interfața web (React + TypeScript: web/src) ── HTTP local ──┐
                                                                 │
serverul local (FastAPI: app/api) ───────────────────────────────┘
  └─ serviciile (app/services) ─ predicțiile, echipele, evaluarea, ligile
       └─ statistici, algoritmi, evaluare, date (neschimbate)
```

- **`app/api`** traduce rezultatele serviciilor în JSON (`schemas.py`, `server.py`, `analysis.py`) și nu calculează nimic. Testul de arhitectură verifică faptul că nu importă `algorithms/`, `ui/` sau `visualization/`; nu importă nici Qt, nici matplotlib.
- **`web/`** doar afișează ce trimite serverul. Scrierea românească a numerelor și a datelor este copiată în `web/src/format.ts`; nimic nu este prezis, antrenat sau evaluat în TypeScript. Graficele desenează numere calculate de server.
- Ce era în fereastra Qt și trebuia și serverului a trecut în servicii, ca ambele interfețe să folosească același cod: procesul de lucru (`app/services/processes.py`), deschiderea ligilor (`registry.py`), căile imaginilor (`images.py`), propozițiile paginilor (`explanations.py`), numele subseturilor evaluării (`labels.py`) și zilele unui meci ipotetic (`DataCatalog.hypothetical_days`).

### 18.2. Serverul local

`python -m app.api [--port N] [--preferences FIȘIER] [--with-window]` ascultă doar pe acest calculator (127.0.0.1). Cu portul 0 (implicit) alege sistemul un port liber, iar primul rând scris este `PITCHSENSE_PORT=<port>`, din care fereastra află adresa. Apoi calculează predicțiile fiecărei ligi în procesul de lucru, întâi liga aleasă ultima dată; `/api/status` spune care sunt gata, iar ecranele le arată pe măsură ce sosesc.

| Rută | Ce întoarce |
|---|---|
| `/api/leagues`, `/api/status`, `/api/days`, `/api/day/{zi}` | ligile, starea predicțiilor, zilele cu meciuri, meciurile unei zile cu „meciul zilei” |
| `/api/match/{ligă}` | pagina unui meci: fiecare model cu propoziția lui, scorurile Poisson 0–0…6–6, cum vin echipele; și meciurile ipotetice |
| `/api/season/{ligă}` | echipele și zilele unui sezon (pentru „Alt meci”) |
| `/api/standings/{ligă}` | clasamentul la final sau înaintea unei zile, cu forma |
| `/api/team/{ligă}` | sezonul unui club: bilanț acasă, în deplasare și total, formă, șuturi, istoricul Elo, profilul K-Means, grupurile sezonului |
| `/api/review/{ligă}` | predicțiile unui model pentru meciurile jucate ale unui sezon, față de rezultate |
| `/api/about`, `/api/season-check/{ligă}`, `/api/evaluation/{ligă}`, `/api/leagues-comparison` | Analiză; ultimele două pot rula și backtestul (POST) |
| `/api/update` (POST) | descarcă sezonul în desfășurare, la cererea utilizatorului, apoi recitește ligile |
| `/api/preferences` | liga și echipa utilizatorului |
| `/api/images/…` | stemele, imaginile ligilor și fotografiile stadioanelor |

CORS permite doar originile ferestrei Tauri și pe cea a lui Vite din dezvoltare. Opțiunea `--with-window` (a ferestrei) oprește serverul când i se închide intrarea standard, adică atunci când procesul ferestrei se termină oricum, chiar oprit forțat (verificat cu `kill -9`); procesul de lucru se oprește odată cu serverul. `--self-test` (`app/api/self_test.py`) pornește serverul pe un port liber și îi pune fiecare tip de întrebare, iar `--update` descarcă sezonul în desfășurare și iese: cu ele se verifică pachetele, pentru că fereastra are nevoie de ecran.

### 18.3. Fereastra

`web/src-tauri/src/lib.rs` pornește serverul împachetat (`server/pitchsense-server`) sau, în dezvoltare, Python-ul din `.venv`, citește portul anunțat, îl dă interfeței prin comanda `backend_url` și oprește serverul la închidere. Politica de securitate a conținutului permite doar serverul local. Pe Windows, instalarea se face în Program Files, ca folderul `%LOCALAPPDATA%\PitchSense` să rămână doar al datelor utilizatorului.

### 18.4. Ecranele

Layoutul A, ales de echipă: o singură bară laterală cu sigla, ecranele cu iconițe (Meciuri · Clasament · Echipe · Predicții · Analiză), ligile, „Echipa ta”, actualizarea datelor și sursele. Culorile fiecărei ligi sunt variabile CSS (`web/src/theme.ts`, aceleași valori ca `app/ui/themes.py`).

- **Meciuri.** Cardul „Meciul zilei” cu imaginea ligii, zilele, toate ligile (cea aleasă prima), orice sezon, modelul ales; în dreapta, „Echipa ta” (rândurile ei pun echipele una sub alta, ca numele să nu fie tăiate) și clasamentul pe scurt. „Alt meci…” prezice oricare două echipe ale unui sezon, la o zi aleasă.
- **Pagina meciului.** Capul în culorile ligii meciului, peste fotografia stadionului gazdelor; fiecare model cu bara lui de probabilități și propoziția lui; cum vin echipele, față în față, cu valoarea mai bună evidențiată; golurile așteptate, cele mai probabile scoruri și toate scorurile 0–0…6–6. Cifrele fiecărei celule au culoarea (alb sau negru) care se citește mai bine pe ea, cu contrastul de cel puțin 4,5:1 verificat pentru fiecare ligă.
- **Clasament.** Orice sezon, la final sau înaintea unei zile, cu stemele și forma; un clic deschide echipa.
- **Echipe.** Capul clubului peste fotografia stadionului; bilanțul ca tabel aliniat (acasă, în deplasare, total); șuturile echipei față de ale adversarilor; meciurile (toate, la cerere); „Profilul echipei”, fără descrierea K-Means (rămasă în Analiză); graficele Elo și ale grupurilor (Recharts, încărcate la prima afișare). Sezonul ales este desenat în accentul ligii, celelalte în gri, ca fundal.
- **Predicții** (cererea echipei). Pentru un sezon și un model: cât la sută din meciuri a nimerit, cum a anticipat fiecare fel de rezultat și lista meciurilor, filtrată (toate, nimerite, ratate, surprize) și ordonată (cele mai recente, cele mai mari surprize, cele mai sigure). O surpriză este un rezultat căruia modelul îi dădea sub 20% (`SURPRISE_CHANCE`). Fiecare listă încercuiește cipul rezultatului care s-a întâmplat.
- **Analiză.** Cinci file: algoritmii pe înțeles (și profilurile K-Means), sezonul în desfășurare, modelele (tabele cu coloane măsurate, calibrarea și matricea de confuzie alăturate, defalcările, acordul), ligile (carduri, tabele ale căror coloane numerice împart lățimea, abilitatea și avantajul gazdelor) și sursele. Fiecare card se termină odată cu conținutul lui.
- **Schimbarea ligii.** Ca în fereastra Qt: pagina în culorile noii ligi apare dintr-un cerc din colțul stânga-sus, cu marginea din două valuri care se calmează (0,8 s). Folosește tranzițiile de vizualizare ale browserului, cu un poligon al cărui număr de puncte rămâne același în fiecare cadru; unde ele lipsesc sau utilizatorul a cerut mai puțină mișcare, schimbarea este imediată.

### 18.5. Fotografiile stadioanelor

Echipa a cerut imagini cu stadioane și jucători și a permis imagini protejate în acest proiect privat. `tools/stadiums.py` citește terenul din articolul Wikipedia al fiecărui club (articolele găsite pentru steme), apoi imaginea principală a articolului stadionului (sau imaginea din infobox), la 1024 px lățime; desenele, siglele, hărțile și planurile sunt respinse. Cluburile cu același stadion împart fotografia. `app/assets/stadiums/sources.json` dă, pentru fiecare club, stadionul, articolul și fișierul. Fotografiile aparțin autorilor lor; sunt folosite doar în proiectul privat și nu se publică.

### 18.6. Împachetarea

`python packaging/build.py` reconstruiește datele, construiește serverul cu PyInstaller (`packaging/server.spec`: fără Qt și matplotlib) și fereastra cu Tauri, cu serverul ca resursă și versiunea din `app/__init__.py`: pe macOS `PitchSense.app` într-un `.dmg`, pe Windows un program de instalare (NSIS). Fluxul GitHub Actions pentru Windows rulează ambele suite de teste, construiește pachetul, încearcă `--update` și `--self-test` ale serverului împachetat, instalează pachetul fără întrebări și rulează autoverificarea serverului instalat.

### 18.7. Verificare

Rulări din 2026-10-16:

- **Teste.** Toate cele 849 de teste Python trec, pe macOS și pe Windows (GitHub Actions); `ruff check` și `ruff format --check` nu găsesc nimic. Serverul este verificat de `tests/test_api.py` și `tests/test_api_analysis.py` (fiecare rută, pe datele sintetice: pagina meciului și meciul ipotetic, clasamentul, pagina echipei, predicțiile față de rezultate, Analiză și backtestul ei, actualizarea reușită sau eșuată, preferințele, imaginile, oprirea odată cu fereastra, scrierea UTF-8 pe orice consolă, așteptarea unei pregătiri pornite, autoverificarea), `tests/test_services.py` verifică `PredictionService.review`, iar `tests/test_architecture.py` și `tests/test_environment.py` verifică straturile, versiunile fixe și versiunea unică. Interfața web are 17 teste Vitest (scrierea românească, culorile celulelor și contrastul lor în fiecare ligă, sigla stemelor întunecate, valul, filtrele ecranului Predicții, nota actualizării), iar `npm run build` verifică tipurile TypeScript. Codul Rust trece `cargo fmt --check` și `cargo clippy -- -D warnings`.
- **Verificare vizuală.** Fiecare ecran a fost deschis cu datele reale, în browser, la 1440 × 900 și la 1024 × 700: Meciuri, pagina meciului (jucat, programat, ipotetic), Clasament, Echipe (cu ambele grafice), Predicții, cele cinci file ale Analizei, dialogurile „Alt meci” și „Echipa ta”, valul schimbării ligii (oprit la jumătate). La 1024 px niciun ecran și niciun tabel nu se derulează în lateral. Fereastra Tauri a fost verificată din `tauri dev`, dintr-o aplicație de test și din pachet.
- **Procese.** Serverul și procesul lui de lucru se opresc când fereastra se închide din meniu și când este oprită forțat (`kill -9`).
- **Pachete.** Versiunea a rămas 0.3.0.
  - macOS: `.dmg` de 86 MB (aplicația 141 MB, din care serverul 91 MB). Autoverificarea serverului trece 13 din 13 din `dist/` și din imaginea `.dmg` montată doar pentru citire; aplicația deschisă din `dist/` își pornește serverul și arată ecranele, iar la închidere nu rămâne niciun proces.
  - Windows (GitHub Actions): toate testele trec, programul de instalare are 68 MB. Serverul împachetat descarcă sezonul în desfășurare (`--update`: 297 de meciuri jucate și 1.455 programate în 5 ligi), autoverificarea lui trece, iar după instalarea fără întrebări în *Program Files* trece și autoverificarea serverului instalat.

### 18.8. Limitări

- Valul schimbării ligii cere tranzițiile de vizualizare ale browserului: în fereastra de macOS ele există de la Safari 18 (WebKit-ul sistemului); cu unul mai vechi, schimbarea este imediată.
- Un meci ipotetic este calculat la cerere, în 3–8 secunde pe datele reale, cât folosește toate meciurile de până la acea zi.
- Ecranele arată o ligă abia după ce i s-au calculat predicțiile (aproximativ 8 secunde pe ligă, la pornire).
- Fotografiile arată stadionul de acum al fiecărui club, nu pe cel din sezonul ales; cinci cluburi nu au fotografie (Arles, Carpi, Evian Thonon Gaillard, Nancy, Numancia), iar capul lor păstrează culoarea ligii.
- Pachetele nu sunt semnate. Pe Windows, fereastra are nevoie de WebView2 (inclus în Windows 10 și 11 actualizate; programul de instalare îl aduce dacă lipsește).

### 18.9. Scoaterea ferestrei PySide6

La acceptarea etapei (2026-10-16), echipa a cerut ca fereastra PySide6 să fie scoasă, pentru că interfața web face tot ce făcea ea.

- **Ce a plecat:** `app/ui/` (cu autoverificarea ei), `app/visualization/` (graficele matplotlib și paleta lor), `app/__main__.py` (`python -m app`), `packaging/pitchsense.spec`, `packaging/icons.py` și testele lor (`test_ui`, `test_themes`, `test_brand`, `test_transition`, `test_charts`, `test_self_test`, `test_main`, `test_icons` și testele de pornire ale ferestrei din `test_paths`). Iconițele ferestrei Tauri fuseseră desenate din aceeași siglă și rămân în `web/src-tauri/icons/`.
- **Ce s-a mutat:** imaginile (steme, imaginile ligilor, fotografiile stadioanelor) în `app/assets/`. PySide6 și matplotlib nu mai sunt dependențe ale aplicației; Qt rămâne doar pentru instrumentele imaginilor (`tools/crests.py`, `tools/stadiums.py`), în opțiunea `tools` (`python -m pip install -e ".[tools]"`).
- **Ce a preluat serverul:** comportamentul de la pornire al ferestrei. O copiere eșuată a jurnalelor livrate sau a sezonului în desfășurare este raportată, iar pornirea continuă. O bază de date lipsă este explicată, iar fereastra Tauri arată mesajul în loc să aștepte. Un backtest eșuat răspunde cu motivul, iar datele încărcate merg mai departe.
- **Testele:** `tests/test_integration.py` parcurge acum lanțul până la răspunsurile serverului (fișiere brute → bază de date → jurnal → evaluare → server), cu aceleași verificări ca înainte. Testul de arhitectură cere ca nimic din `app/` să nu importe Qt sau matplotlib. Rămân 682 de teste Python, care rulează în aproximativ 10 secunde (înainte, 852 în aproximativ 52 de secunde), și 18 teste ale interfeței web.
- **Verificare după scoatere (2026-10-16):** pe macOS, pachetul reconstruit de la zero (`.dmg` de 86 MB) își trece autoverificarea din `dist/` și din imaginea `.dmg` montată doar pentru citire; aplicația pornește normal, iar cu baza de date mutată temporar arată motivul în fereastră. Pe Windows (GitHub Actions) trec toate cele 682 de teste, programul de instalare are 67 MB, `--update` din pachet descarcă sezonul, iar autoverificarea trece atât pentru serverul din pachet, cât și pentru cel instalat.

## 19. Predicții mai bune (Faza 23)

Echipa a cerut, după Faza 22: precizia exactă pe meciurile în care un model e sigur, arătată în aplicație; comparația cu casele de pariuri, ca reper; și trei îmbunătățiri ale algoritmilor (Elo cu diferența de goluri, Poisson cu meciurile recente mai importante și corecția Dixon–Coles, mai multe caracteristici pentru regresia logistică).

### 19.1. Măsurarea

- **Când modelul e sigur.** `confident_accuracy` (`app/evaluation/metrics.py`) dă acuratețea pe meciurile în care cea mai mare probabilitate a modelului este cel puțin un prag, cu numărul și partea lor; evaluatorul o calculează pentru pragurile 50%, 60%, 65% și 70% (`CONFIDENCE_THRESHOLDS`), pentru fiecare model cu probabilități. `SeasonReview.when_sure` face același lucru pentru meciurile unui sezon.
- **Cotele.** `app/data/odds.py` citește media cotelor din fișierele brute (`BbAvH/D/A` până în 2018/19, `AvgH/D/A` din 2019/20); un meci fără toate trei este lăsat deoparte, o valoare greșită sau imposibilă (cel mult 1) este o eroare cu rândul ei. `build_database` le păstrează în tabelul `market_odds`, separat de meciuri, pe care modelele nu îl citesc niciodată. Probabilitățile se obțin scoțând marja proporțional.
- **Casele de pariuri.** `app/evaluation/bookmakers.py` face din cote un rând „Bookmakers” al jurnalului, pentru fiecare meci de evaluare cu cote, și îl compară meci cu meci cu fiecare model (scorul Brier); `python -m app.evaluation.bookmakers` tipărește comparația fiecărei ligi. `EvaluationService` o adaugă rezultatelor (`EvaluationResults.bookmakers`), iar o bază de date construită înainte de Faza 23, fără cote, doar o lasă deoparte.
- **Serverul și ecranele.** `ModelEvaluation.confident`, `Evaluation.bookmakers`, `Review.sure` și `ReviewedMatch.confidence` (`app/api/schemas.py`). Analiză → Modele are două carduri noi, „Când modelul e sigur” (modelele și cele patru praguri) și „Față de casele de pariuri” (măsurile, pragul de 65% și diferențele meci cu meci, cu nota că cotele sunt doar un reper). Predicții are cardul „Când modelul era sigur” (cele patru praguri ale sezonului, cel de 65% evidențiat) și filtrul „Sigure (peste 65%)”; ordinea „Cele mai sigure predicții” folosește acum `confidence`.

### 19.2. Algoritmii

Fiecare îmbunătățire este o opțiune în plus a grilei de calibrare a modelului ei, aleasă sau nu pentru fiecare ligă doar pe sezoanele 2007/08–2009/10 (`app/prediction/settings.py`, `league_settings` cu argumentele `goal_margin`, `half_life`, `rho`, `extra_features`). Fără ele, modelele dau exact predicțiile de dinainte.

- **Elo** (`docs/algorithms/elo.md`, Ec. 7): ponderea diferenței de goluri a World Football Elo Ratings; aleasă în Premier League, La Liga și Bundesliga.
- **Poisson** (`docs/algorithms/poisson.md`, Ec. 6–7): ponderi $2^{-j/h}$ pentru meciurile unei echipe (alese peste tot, în afară de Serie A) și corecția Dixon–Coles a scorurilor 0–0, 0–1, 1–0, 1–1, cu $\rho$ limitat astfel încât niciun scor să nu piardă mai mult de jumătate din probabilitate (aleasă în toate ligile).
- **Regresia logistică** (`docs/algorithms/logistic_regression.md`, secțiunea 4): distanța Elo, $|$diferența Elo$|$, și diferența golurilor așteptate de Poisson; prima aleasă doar în La Liga, a doua în Premier League, La Liga și Serie A. `predict_history` dă caracteristicilor predicțiile Poisson pe care le-a calculat deja, ca modelul să nu ruleze de două ori.

Rezultatele, ligă cu ligă și față de setările de dinainte: `docs/leagues.md`, secțiunile 5–7. Pe scurt: Poisson s-a îmbunătățit real, regresia logistică nu s-a schimbat real pe toate ligile la un loc, iar Elo cu ponderea golurilor este cu foarte puțin mai slab pe sezoanele de evaluare, deși calibrarea l-a ales. Opțiunile nu au fost schimbate după ce s-au văzut aceste rezultate.

### 19.3. Verificare

Rulări din 2026-10-16:

- **Date.** Baza de date a fost reconstruită (`python -m app.data.build_database`, toate sezoanele complete) cu cotele: toate meciurile de evaluare au cote, în afară de unul din Serie A. Calibrarea tuturor ligilor (`league_calibration`, aproximativ 5 minute) a fost rulată de două ori: a doua oară cu grilele lărgite, aceleași valori. Jurnalele celor cinci ligi au fost reconstruite (aproximativ 6,5–10 s pe ligă) și sunt identice octet cu octet la o nouă rulare, inclusiv după ce Poisson a început să fie împărțit cu caracteristicile regresiei logistice.
- **Teste.** Testele noi verifică exemple calculate de mână (ponderea golurilor, $\tau$, ponderile meciurilor recente, caracteristicile noi, acuratețea când modelul e sigur, cotele și marja), invariantele (suma ratingurilor, suma tabelului și golurile așteptate după corecție), cazurile limită ($\rho$ limitat, meciuri fără cote), intrările greșite, absența scurgerii de informații cu caracteristicile noi și faptul că fiecare alegere a calibrării are măsura modelului rulat cu ea. Un test leagă textele din Analiză de ligile care folosesc fiecare opțiune.
- **Ecrane.** Analiză → Modele și Predicții au fost deschise cu datele reale la 1280 × 900 și 1024 × 800; niciun tabel nu se derulează în lateral.

### 19.4. Limitări

- Câștigurile sunt mici (cel mult 0,004 la scorul Brier într-o ligă), iar casele de pariuri rămân real mai bune decât fiecare model, cu 0,009–0,026 la scorul Brier.
- Grilele au acum mult mai multe alegeri pe aceleași trei sezoane de calibrare, deci alegerea poate urma zgomotul (cazul ponderii golurilor la Elo).
- Pregătirea predicțiilor unei ligi durează puțin mai mult (aproximativ o secundă), pentru că regresia logistică are până la șapte caracteristici.

## 20. Setul de date și perioadele

Sursa datelor este Football-Data.co.uk: cinci ligi (Premier League, La Liga, Serie A, Bundesliga, Ligue 1), fiecare cu 20 de sezoane încheiate, 2006/07–2025/26 (36.197 de meciuri). Perioadele sunt aceleași pentru toate ligile. Sezonul în desfășurare (2026/27) este descărcat separat și nu face parte din evaluare (secțiunea 15).

| Perioadă | Rol |
|---|---|
| 2006/07 | Încălzire: construiește ratingurile și istoricul; nu este evaluată. |
| 2007/08–2009/10 | Calibrare: se aleg hiperparametrii; rezultatele nu sunt raportate. |
| 2010/11–2025/26 | Evaluarea raportată: 16 sezoane; 6.080 de meciuri în fiecare ligă cu 20 de echipe, 4.896 în Bundesliga, 5.757 în Ligue 1; 28.893 în total. |

## 21. Tehnologii

| Componentă | Versiune | Rol |
|---|---|---|
| Python | 3.14 | limbajul aplicației |
| PySide6-Essentials | 6.11.2 | interfața grafică (Qt) până în Faza 22; acum doar pentru instrumentele imaginilor |
| NumPy | 2.5.3 | calculele numerice din algoritmi |
| pandas | 3.0.6 | citirea și prelucrarea datelor |
| matplotlib | 3.11.2 | grafice, până în Faza 22 (înlocuit de Recharts) |
| SQLite (`sqlite3`, inclus în Python) | – | stocarea datelor prelucrate |
| pytest | 9.1.1 | testare |
| ruff | 0.16.10 | verificarea și formatarea codului |
| PyInstaller | 6.22.3 | construirea pachetelor de instalare |
| Plus Jakarta Sans (font, SIL Open Font License 1.1) | cinci grosimi statice | textul interfeței și al graficelor (din Faza 21, în locul lui Libre Franklin), inclus în `app/ui/assets/fonts/` |
| Barlow Condensed (font, SIL Open Font License 1.1) | patru grosimi statice | titlurile, cifrele mari, scorul și navigarea, inclus în `app/ui/assets/fonts/` |
| Kanit (font, SIL Open Font License 1.1) | Black Italic și ExtraBold Italic | sigla și numele de lângă ea (Faza 21), inclus în `app/ui/assets/fonts/` |
| FastAPI / uvicorn | 0.143.2 / 0.54.0 | serverul local al interfeței web (Faza 22) |
| httpx2 | 2.13.1 | clientul de test al serverului (doar pentru teste; Starlette 1.8 avertizează cu httpx) |
| Node / npm | 26.12 / 11.20 | construirea interfeței web |
| React / TypeScript / Vite | 19.3.1 / 7.0.2 / 8.3.4 | interfața web |
| Recharts | 3.10.1 | graficele interfeței web |
| Vitest, Testing Library, jsdom | 5.0.5, 16.3.3, 30.1.3 | testele interfeței web |
| Rust / Tauri | 1.99 / 2.12.4 | fereastra de desktop a interfeței web |

## 22. Decizii tehnice

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
| Barlow Condensed pentru titluri și cifre, Plus Jakarta Sans pentru text (Libre Franklin până în Faza 21), ambele incluse în aplicație | O literă condensată de sport pentru ce se citește dintr-o privire și o literă geometrică, ca în aplicațiile din referințe, pentru text; aceleași pe macOS, pe Windows și în grafice, cu diacriticele românești; licențele permit includerea. |
| Stilul Qt Fusion, o paletă Qt întunecată și o singură foaie de stil | Aplicația arată la fel pe ambele sisteme și oricare ar fi tema sistemului. |
| Bara de sus cu ecranele și panoul ligilor în stânga, ca la LiveScore | Ecranele și ligile se aleg cu un singur clic, iar liga aleasă se vede mereu. |
| Sigla, steagurile și ecusoanele sunt desenate cu QPainter; literele siglei sunt conturul fontului Kanit, inclus în aplicație (până în Faza 21: cercuri și dreptunghiuri) | Desenul este exact la fel pe orice sistem, pentru că fontul vine cu aplicația, și se poate testa, atât geometric, cât și citind culorile pixelilor. |
| Echipele au ecusoane cu trei litere, ligile steagul țării | Stemele cluburilor și siglele ligilor sunt mărci înregistrate și nu fac parte din date. |
| Serviciile unei ligi sunt deschise la prima alegere și păstrate | Pornirea nu așteaptă cele cinci ligi; schimbarea ligii este imediată după prima dată. |
| Alegerile utilizatorului (liga, echipa) sunt într-un fișier JSON în folderul utilizatorului | Pachetul rămâne nemodificat; un fișier deteriorat sau imposibil de scris nu oprește aplicația. |
| Textul afișat este tradus într-un singur loc (`formatting.py`, `labels.py`) | Jurnalele, testele și codul păstrează identificatorii în engleză; afișarea românească este consecventă. |
| Cardul Acasă spune dacă avantajul modelului cu cel mai mic scor Brier este real | Un clasament după diferențe de 0,0001 ar sugera un câștigător acolo unde nu există unul. |
| Versiunea este scrisă doar în `app/__init__.py` | Pachetele, `pyproject.toml` și fereastra arată mereu aceeași versiune. |
| Iconițele pachetelor (`.icns`, `.ico`) sunt scrise de noi, cu imagini PNG desenate din siglă | Iconița urmează mereu sigla și nu este nevoie de o bibliotecă de imagini nouă. |
| Un fișier `VERSION` în folderul jurnalelor; o actualizare înlocuiește jurnalele vechi | Jurnalele calculate de modele mai vechi nu mai pot ajunge în aplicația nouă; în aceeași versiune, jurnalele reconstruite rămân. |
| Sezonul în desfășurare este descărcat doar când utilizatorul apasă „Actualizează datele” | Aplicația rămâne utilizabilă fără internet; datele unei predicții se știu mereu (ora ultimei actualizări este afișată). |
| Rezultatele de la Football-Data, calendarul de la openfootball (CC0) | Rezultatele vin din aceeași sursă ca istoricul; fișierul cu meciurile viitoare de la Football-Data acoperă doar câteva zile și este gol în pauzele competiționale, pe când calendarul openfootball are tot sezonul și poate fi folosit liber. |
| Numele echipelor din calendar sunt potrivite din meciurile jucate în ambele surse, nu dintr-un tabel scris de mână | Funcționează pentru orice ligă și sezon, fără întreținere; o echipă nesigură este raportată, nu ghicită. |
| Toate meciurile programate sunt prezise din ziua de după ultimul meci jucat | Scorurile inventate ale înlocuitorilor nu pot influența nicio predicție, iar predicția folosește tot ce se știe în acel moment. |
| Fișierele noi înlocuiesc folderul vechi doar după ce au trecut toate verificările | O descărcare eșuată sau un fișier deteriorat nu poate lăsa aplicația fără date. |
| Certificatele sistemului pentru HTTPS, fără o bibliotecă nouă | Python de pe python.org nu are certificate proprii pe macOS; cele ale sistemului sunt verificate de sistem. |
| Pachetul livrează instantaneul sezonului în desfășurare de la construcție | Aplicația instalată are meciurile programate și fără o primă actualizare. |
| Meniul Meciuri · Clasament · Echipe · Analiză, cu meciurile pe zile ca prim ecran | Decizia echipei: aplicația pornește de la meciuri, ca aplicațiile de scoruri; evaluarea este pentru cine o caută, în Analiză. |
| Lista meciurilor arată un singur model, implicit regresia logistică | Cel mai mic scor Brier pe cele cinci ligi, cu o diferență reală; o medie a modelelor ar fi un model nou, neevaluat. |
| Stemele reale ale cluburilor, de pe Wikipedia, la 128 px, cu sursa fiecăreia | Decizia echipei; folosite doar pentru recunoașterea echipelor, într-un depozit privat și în pachete. |
| Stemele întunecate stau pe un disc deschis | Altfel dispar pe tema întunecată; regula se calculează din pixelii stemei, nu dintr-o listă. |
| Imaginile ligilor: imagini promoționale DAZN alese de echipă, cu sursa afișată | Decizia echipei, după acceptarea Fazei 19 (înainte: fotografii libere de stadioane); folosite doar în proiectul privat. |
| Opțiunea `--update` a aplicației | Actualizarea din pachet poate fi verificată automat pe macOS și pe Windows, fără să apeși un buton; tot ea poate actualiza datele fără fereastră. |
| Predicțiile tuturor ligilor se pregătesc în fundal, pe rând | Ecranul Meciuri arată toate ligile; liga aleasă este gata prima, iar fereastra nu se blochează. |
| Sigla PS tăiată, albă deasupra și în accentul ligii dedesubt (Faza 21) | Decizia echipei, după ce monogramele pe pătrate semănau cu iconița Photoshop: litere îndrăznețe, ca la aplicațiile de scoruri, care iau culorile ligii afișate. |
| Suprafețe neutre comune; fiecare ligă are doar accentul, culoarea adâncă și imaginea ei; culorile formei și ale modelelor rămân aceleași | Decizia echipei: schimbarea ligii trebuie să se vadă, dar prima versiune, cu suprafețele colorate în nuanța ligii, părea toxică; în referințe, culoarea vie stă pe forme pline pe un fond neutru. Culorile cu sens (formă, model) au fost validate pentru daltoniști. |
| La schimbarea ligii se restilizează doar fereastra | De trei–patru ori mai repede decât restilizarea întregii aplicații, deci animația începe aproape imediat. |
| Animația desenează, pe un strat opac, imaginea nouă a ferestrei și imaginea veche în afara unui cerc cu valuri, calculat ca un singur poligon | Nimic de sub strat nu se redesenează în timpul animației (prima versiune, transparentă, redesena toată fereastra la fiecare cadru și sacada); un cadru durează 4–9 ms la rezoluția Retina. |
| Antetul desenează imaginea ligii direct, la rezoluția ecranului, și o trece în culoarea propriei margini, nu o extinde cu inteligență artificială | Nimic nu este inventat în imagine și nu se pierde calitate (prima versiune, cu o imagine intermediară și o copie estompată, o desena la jumătate din rezoluție pe Retina). |
| Piese adaptive (`ResponsiveBox`, `ReflowGrid`, rânduri care trec pe două linii) în locul unei lățimi minime mari | Aplicația se poate folosi pe ecrane de laptop mici, fără bară de derulare orizontală. |
| Interfața refăcută pe web: React și TypeScript într-o fereastră Tauri, peste un server FastAPI local (Faza 22) | Decizia echipei: o interfață mai flexibilă decât Qt, cu aceleași servicii Python; Tauri folosește vizualizatorul web al sistemului, deci pachetul e mic, iar FastAPI validează răspunsurile cu aceleași tipuri. |
| Serverul ascultă doar pe 127.0.0.1, pe un port ales de sistem, anunțat pe primul rând | Nimeni din afara calculatorului nu îl poate folosi, iar două aplicații pornite nu se ciocnesc la port. |
| Serverul se oprește când i se închide intrarea standard | Nu rămâne niciun server pornit fără fereastră, nici când fereastra este oprită forțat. |
| Graficele interfeței web sunt desenate în interfață (Recharts și grile CSS), cu numerele calculate de server | Decizia echipei; graficele urmează culorile ligii, au indicii la trecerea mausului și se încarcă doar când sunt afișate. |
| Ecranul Predicții, cu surprizele definite ca rezultate cu șansă sub 20% | Cererea echipei; pragul este scris o singură dată (`SURPRISE_CHANCE`) și explicat pe ecran. |
| Fotografiile stadioanelor de pe Wikipedia, cu sursa fiecăreia | Cererea echipei, care a permis imagini protejate în proiectul privat; aceeași metodă ca la steme. |
