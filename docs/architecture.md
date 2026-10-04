# Arhitectura aplicației PitchSense

Acest document descrie structura aplicației, fluxul datelor și deciziile tehnice luate până acum (fazele 0 și 1). Se actualizează ori de câte ori structura se schimbă.

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

## 6. Formatul comun al predicției

Fiecare model care estimează rezultatul unui meci întoarce:

- numele modelului;
- probabilitățile `(p_home, p_draw, p_away)`, mereu în această ordine: victoria gazdelor, egal, victoria oaspeților. Valorile sunt nenegative, iar suma lor este 1 (cu toleranța 1e-9);
- opțional, doar pentru modelul Poisson: numărul așteptat de goluri și matricea probabilităților pentru fiecare scor.

K-Means nu prezice rezultatul meciului. El întoarce grupuri (clustere) de echipe cu profiluri statistice asemănătoare.

## 7. Backtesting cronologic

Meciurile sunt parcurse în ordinea datelor. Pentru fiecare zi de joc D:

1. modelele care se antrenează (regresia logistică, parametrii modelului Poisson) sunt reantrenate, după un program documentat, doar pe meciurile dinaintea zilei D;
2. fiecare model prezice toate meciurile din ziua D, iar predicțiile sunt salvate;
3. abia apoi se dezvăluie rezultatele din ziua D și se actualizează modelele cu stare (ratingurile Elo).

Metricile se calculează din jurnalul predicțiilor salvate, în aceleași condiții pentru toate modelele.

## 8. Setul de date și perioadele

Sursa datelor este Football-Data.co.uk: La Liga (`SP1`), 20 de sezoane încheiate, 2006/07–2025/26 (7.600 de meciuri).

| Perioadă | Rol |
|---|---|
| 2006/07 | Încălzire: construiește ratingurile și istoricul; nu este evaluată. |
| 2007/08–2009/10 | Calibrare: se aleg hiperparametrii; rezultatele nu sunt raportate. |
| 2010/11–2025/26 | Evaluarea raportată: 16 sezoane, 6.080 de meciuri. |

## 9. Tehnologii

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

## 10. Decizii tehnice

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
