# PitchSense

Aplicație desktop pentru analiza datelor istorice din fotbal și estimarea rezultatelor meciurilor, pentru macOS și Windows. Aplicația folosește patru algoritmi implementați de noi, fără biblioteci gata făcute: ratingul Elo, modelul Poisson, regresia logistică și K-Means.

Proiect de an la disciplina *Analiza și Proiectarea Algoritmilor* (APA), Universitatea Tehnică a Moldovei, Departamentul Ingineria Software și Automatică.
Echipa (grupa TI-251): Goroșevschi Chiril, Cuzmici Nicolae, Păstru Alina.

**Stadiu:** toate etapele, 0–24, sunt încheiate: etapa 24 (actualizarea automată a datelor și orele meciurilor) pe 2026-10-28, etapa 23 (predicții mai bune: precizia când modelul e sigur, comparația cu casele de pariuri și îmbunătățirile celor trei modele de predicție) pe 2026-10-17, etapele 21 (designul refăcut) și 22 (interfața web: React și TypeScript într-o fereastră Tauri, peste un server Python local; fereastra PySide6 a fost scoasă) pe 2026-10-16. Versiunea curentă este 0.6.0 (2026-10-28), cu actualizarea automată și orele locale ale meciurilor; 0.5.1 (2026-10-21) a corectat pornirea lentă și problemele de deschidere ale versiunii 0.5.0 (2026-10-17) pe Windows și macOS; 0.4.0 (2026-10-16) a fost prima cu interfața web. Etapele 18 (sezonul în desfășurare), 19 (interfață centrată pe meciuri) și 20 (pachete și versiunea 0.3.0) au fost adăugate de echipă și încheiate pe 2026-10-15. Fazele 0–12 (planificare și arhitectură, prelucrarea datelor istorice, statisticile echipelor, ratingul Elo, modelul Poisson, regresia logistică, K-Means, motorul de predicție, backtesting cronologic, metricile de evaluare, compararea algoritmilor, interfața grafică, vizualizarea) au fost încheiate pe 2026-10-04, fazele 13 (testare de integrare și finisare), 14 (pachete de instalare pentru macOS și Windows), 15 (cinci ligi) și 16 (identitate vizuală și interfață nouă, în limba română) pe 2026-10-05, iar faza 17 (pachete și versiunea 0.2.0) pe 2026-10-06. Aplicația se pornește din pachetele de instalare sau, din codul sursă, cu `npm run tauri dev` (secțiunea *Pornirea aplicației*).

## Aplicația gata de instalat

Pachetele se descarcă de pe pagina [Releases](https://github.com/kirillthehighest/Pitch-Sense/releases/latest) a depozitului (versiunea curentă: 0.6.0, cu actualizarea automată a datelor). Depozitul este privat, deci pagina se deschide doar pentru cei care au acces la el. Pachetele nu cer Python și conțin deja datele: baza de date cu cele cinci ligi, jurnalele predicțiilor fiecărei ligi, imaginile și sezonul în desfășurare de la data construirii (butonul **Actualizează datele** îl aduce la zi).

| Sistem | Fișier | Cerințe |
|---|---|---|
| macOS | `PitchSense-0.6.0-macOS-arm64.dmg` | Mac cu procesor Apple Silicon, macOS 14 sau mai nou |
| Windows | `PitchSense-0.6.0-Windows-amd64-setup.exe` | Windows 10 sau 11, pe 64 de biți |

**macOS:** deschideți fișierul `.dmg` și trageți `PitchSense` în `Applications`. Pachetul nu are un certificat Apple de dezvoltator, așa că macOS blochează prima deschidere a unei copii descărcate din internet („Apple nu poate verifica…”): deschideți *System Settings → Privacy & Security* și alegeți *Open Anyway* în dreptul mesajului despre PitchSense. Versiunea 0.5.0 era semnată incomplet, iar macOS o declara „deteriorată” fără să permită deschiderea; de la 0.5.1, aplicația este semnată în întregime (semnătură ad-hoc). Pentru 0.5.0 deja copiată în `Applications`, comanda `xattr -dr com.apple.quarantine /Applications/PitchSense.app` din Terminal o deschide.

**Windows:** porniți programul de instalare; aplicația se instalează în *Program Files* și apare în meniul Start. Pachetul nu este semnat, așa că Windows poate afișa „Windows protected your PC”: alegeți *More info*, apoi *Run anyway*. Fereastra folosește WebView2, inclus în Windows 10 și 11 actualizate; dacă lipsește, programul de instalare îl aduce.

La pornire, aplicația citește predicțiile celor cinci ligi, calculate dinainte și livrate în pachet: în câteva secunde sunt toate gata. După **Actualizează datele**, aplicația le calculează din nou, o singură dată (aproximativ 8 secunde pe ligă pe un Mac, mai mult pe un calculator mai lent), și le păstrează pentru pornirile următoare. Aplicația își păstrează fișierele în `~/Library/Application Support/PitchSense` (macOS) sau în `%LOCALAPPDATA%\PitchSense` (Windows); ștergerea acestui folder o readuce la starea de după instalare. După instalarea unei versiuni noi, jurnalele predicțiilor lăsate de versiunea veche sunt înlocuite la prima pornire cu cele noi; liga aleasă și echipa ta rămân.

## Cerințe (pentru codul sursă)

- Python 3.14
- macOS sau Windows
- Node 26 pentru interfața web și Rust pentru fereastra de desktop (pe macOS: `brew install node rustup`, apoi `rustup default stable`)

## Instalare (din codul sursă)

Comenzile se rulează din folderul proiectului.

**macOS**

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

**Windows (Command Prompt)**

```bat
py -3.14 -m venv .venv
.venv\Scripts\activate.bat
python -m pip install -e ".[dev]"
```

După orice modificare a fișierului `pyproject.toml`, rulați din nou ultima comandă.

Pentru interfața web, o singură dată (și după orice modificare a fișierului `web/package.json`):

```bash
cd web
npm ci
```

## Verificare

Cu mediul virtual activat:

```bash
python -m pytest
python -m ruff check .
python -m ruff format --check .
```

Testele folosesc doar date sintetice. `tests/test_integration.py` rulează tot lanțul, de la fișierele CSV la răspunsurile serverului pe care le afișează interfața. Serverul interfeței web este verificat de `tests/test_api.py` și `tests/test_api_analysis.py`, iar interfața web, din folderul `web`, cu:

```bash
npm test
npm run build
```

## Date

Meciurile din cinci ligi, sezoanele 2006/07–2025/26 (36.197 de meciuri), preluate de pe [Football-Data.co.uk](https://www.football-data.co.uk): Premier League (`E0`), La Liga (`SP1`), Serie A (`I1`), Bundesliga (`D1`) și Ligue 1 (`F1`). Fișierele originale se află în `data/raw/<cod>/`. Sursa și verificările făcute la descărcare sunt descrise în [`data/raw/README.md`](data/raw/README.md).

### Sezonul în desfășurare

Pentru meciurile care urmează, aplicația descarcă sezonul în desfășurare (acum 2026/27): rezultatele de până acum de la Football-Data.co.uk și calendarul întregului sezon de la [openfootball/football.json](https://github.com/openfootball/football.json) (domeniu public, CC0). Din etapa 24, aplicația descarcă singură datele când cele pe care le are sunt mai vechi de trei ore (se uită la pornire și apoi la fiecare 10 minute). Tot de la Football-Data vine și lista meciurilor din zilele următoare (`fixtures.csv`), care dă ziua și ora reale ale meciurilor anunțate; calendarul openfootball nu are ora celor mai multe meciuri, iar la La Liga pune toată etapa în aceeași zi. Datele se pot aduce oricând și cu butonul **Actualizează datele** din aplicație sau cu comanda:

```bash
python -m app.data.update
```

Fișierele sunt verificate înainte să le înlocuiască pe cele vechi și sunt păstrate în `data/live/` (nu sunt incluse în git). Fără ele, aplicația arată doar sezoanele încheiate. Toate orele sunt ora locală a stadionului; Football-Data le scrie în ora Marii Britanii, iar aplicația le mută cu o oră pentru La Liga, Serie A, Bundesliga și Ligue 1. Detalii: [`docs/architecture.md`](docs/architecture.md), secțiunile 15 și 20.

## Baza de date

Construiește (sau reconstruiește) baza de date `data/pitchsense.db` din fișierele brute:

```bash
python -m app.data.build_database
```

Comanda verifică toate sezoanele și afișează câte meciuri a salvat din fiecare. Baza de date nu este inclusă în git, așa că rulați comanda după clonarea proiectului și după orice modificare a fișierelor din `data/raw/`.

## Pornirea aplicației

Din folderul `web`, cu mediul virtual Python creat și baza de date construită:

```bash
npm run tauri dev
```

Comanda deschide fereastra de desktop, care pornește singură serverul local (`python -m app.api`) și îl oprește la închidere. Pentru lucrul doar în browser, serverul se poate porni separat, pe portul pe care îl caută interfața în dezvoltare, iar interfața cu `npm run dev` (la `http://localhost:1420`):

```bash
python -m app.api --port 8765
```

Bara laterală are ecranele Meciuri, Clasament, Echipe, Predicții și Analiză, ligile, „Echipa ta” și actualizarea datelor. Ecranul **Predicții** arată, pentru un sezon și un model, meciurile nimerite, ratate și surprizele (rezultate cărora modelul le dădea sub 20%). Detalii: [`docs/architecture.md`](docs/architecture.md), secțiunea 18.

Ecranele:

- **Meciuri:** meciurile fiecărei zile, din toate ligile (liga aleasă prima), din orice sezon, cu stemele cluburilor și probabilitățile modelului ales (implicit regresia logistică); la meciurile jucate, scorul și dacă modelul a nimerit. Sus, cardul „Meciul zilei” al ligii alese (când liga nu joacă în acea zi, următorul ei meci). Un clic pe un meci deschide pagina lui: toate modelele, scorurile probabile (Poisson) și cum vin echipele. „Alt meci…” prezice oricare două echipe ale unui sezon, la o dată aleasă;
- **Clasament:** clasamentul unui sezon, la final sau înaintea unei zile, cu forma fiecărei echipe; un clic pe o echipă îi deschide pagina;
- **Echipe:** pagina unei echipe, peste fotografia stadionului: sezonul în cifre, forma (acasă, în deplasare, total), șuturile, meciurile, profilul echipei, ratingul Elo și grupurile;
- **Predicții:** meciurile nimerite, ratate și surprizele unui model într-un sezon și cât a nimerit când era sigur (peste 50, 60, 65 și 70%);
- **Analiză:** cum funcționează algoritmii, cum au prezis sezonul în desfășurare, compararea modelelor (tabele, calibrare, matricea de confuzie, precizia când modelul e sigur și comparația cu casele de pariuri), comparația celor cinci ligi și sursele datelor și imaginilor.

Liga se alege din bara din stânga; aplicația ia culoarea ei și imaginea ei, iar schimbarea se face cu un val care pornește din colțul din stânga sus. Fereastra se potrivește oricărei lățimi de la 1024 px în sus. După pornire, serverul citește predicțiile fiecărei ligi păstrate de o pornire anterioară (sau livrate în pachet) și calculează doar pe cele care lipsesc, întâi pe cea aleasă (aproximativ 8 secunde pe ligă). „Echipa ta” păstrează echipa pe care o urmăriți: este evidențiată în liste și clasamente, are cardul ei pe ecranul Meciuri și meciul ei devine „Meciul zilei” când joacă în liga aleasă.

Aplicația aduce singură rezultatele și calendarul sezonului în desfășurare când datele ei sunt mai vechi de trei ore, iar butonul **Actualizează datele** le aduce imediat (câteva secunde, cu internet); fără internet, aplicația funcționează cu ultimele date descărcate. Cât timp se pregătesc predicțiile noi, ecranele le arată pe cele de până atunci, apoi se reîmprospătează singure. Panoul din stânga arată când au fost actualizate datele ultima dată. Orele meciurilor sunt ora locală a stadionului; un meci a cărui oră nu a fost anunțată încă scrie asta.

Dacă jurnalul predicțiilor unei ligi lipsește sau nu poate fi citit, butonul **Rulează backtestul** îl construiește din nou (aproximativ 8–10 secunde pe ligă).

## Construirea pachetelor

Din etapa 22, pachetul conține interfața web: fereastra Tauri, cu serverul Python local împachetat înăuntru.

**macOS** (pe un Mac cu Apple Silicon, cu mediul virtual activat, Node și Rust instalate):

```bash
python packaging/build.py
```

Comanda reconstruiește baza de date și jurnalele predicțiilor celor cinci ligi, descarcă sezonul în desfășurare (cu internet), toate intrând în pachet, construiește serverul cu PyInstaller (`packaging/server.spec`) și fereastra cu Tauri, și produce `dist/PitchSense.app` și `dist/PitchSense-0.6.0-macOS-arm64.dmg`. Versiunea este scrisă într-un singur loc, `app/__init__.py`.

**Windows:** pachetul se construiește pe GitHub, cu fluxul „Windows package” (`.github/workflows/package.yml`): pe pagina *Actions* a depozitului, *Windows package → Run workflow*. Fluxul rulează testele Python și pe cele ale interfeței web pe Windows, construiește programul de instalare (`PitchSense-0.6.0-Windows-amd64-setup.exe`, care instalează aplicația în *Program Files*), îl verifică și îl păstrează 30 de zile ca *artifact* (`PitchSense-Windows`). Pe un calculator cu Windows, cu Node și Rust, se poate folosi și `python packaging/build.py`.

Serverul unui pachet se poate verifica automat, fără fereastră: `--self-test` îl pornește pe un port liber, îi pune fiecare tip de întrebare și se termină cu codul 0 dacă totul a funcționat; `--update` descarcă sezonul în desfășurare și iese.

```bash
dist/PitchSense.app/Contents/Resources/server/pitchsense-server --self-test
```

Din codul sursă, aceeași verificare este `python -m app.api --self-test`, iar actualizarea `python -m app.api --update`.

## Evaluare

Alege hiperparametrii fiecărui model, pentru fiecare ligă, pe sezoanele de calibrare ale ligii (valorile sunt deja în `app/prediction/settings.py`; comanda le reproduce):

```bash
python -m app.evaluation.league_calibration
```

Rulează toate modelele cronologic pe sezoanele de evaluare și salvează jurnalul predicțiilor fiecărei ligi în `data/results/backtest_<cod>.csv`:

```bash
python -m app.evaluation.backtesting
```

Calculează măsurile de evaluare (acuratețe, scor Brier, pierdere logaritmică, calibrare) pentru fiecare model al unei ligi (aici La Liga):

```bash
python -m app.evaluation.evaluator SP1
```

Compară modelele unei ligi meci cu meci, pe sezoane, pe rezultate și pe tipuri de meciuri:

```bash
python -m app.evaluation.comparison SP1
```

Compară ligile între ele:

```bash
python -m app.evaluation.leagues
```

Compară modelele fiecărei ligi cu casele de pariuri (media cotelor dinaintea meciurilor, fără marja lor; cotele sunt doar un reper și nu intră în niciun model):

```bash
python -m app.evaluation.bookmakers
```

### Imaginile

Stemele cluburilor vin de pe Wikipedia, la rezoluție mică (`tools/crests.py`), iar fotografiile stadioanelor de pe Wikipedia și Wikimedia Commons (`tools/stadiums.py`); instrumentele se rulează doar ca să le reîmprospăteze și au nevoie de Qt (`python -m pip install -e ".[tools]"`). Imaginile ligilor sunt imagini promoționale DAZN, alese de echipă. Stemele, fotografiile și imaginile aparțin deținătorilor lor: sunt folosite doar ca să recunoști echipele și ligile și rămân în depozitul privat și în pachete.

## Documentație

- [`docs/architecture.md`](docs/architecture.md): arhitectura aplicației, fluxul datelor și deciziile tehnice.
- [`docs/evaluation.md`](docs/evaluation.md): măsurile de evaluare și rezultatele modelelor în La Liga.
- [`docs/comparison.md`](docs/comparison.md): compararea algoritmilor în La Liga.
- [`docs/leagues.md`](docs/leagues.md): comparația celor cinci ligi, a modelelor cu casele de pariuri și precizia când modelele sunt sigure.
- [`docs/brand.md`](docs/brand.md): identitatea vizuală: sigla, culorile fiecărei ligi, literele, animația schimbării ligii și regulile interfeței.
- `docs/algorithms/`: câte un document pentru fiecare algoritm: [`elo.md`](docs/algorithms/elo.md) (ratingul Elo), [`poisson.md`](docs/algorithms/poisson.md) (modelul Poisson), [`logistic_regression.md`](docs/algorithms/logistic_regression.md) (regresia logistică), [`kmeans.md`](docs/algorithms/kmeans.md) (K-Means).

## Etape

0. Planificare și arhitectură
1. Prelucrarea datelor istorice
2. Statisticile echipelor
3. Ratingul Elo
4. Modelul Poisson
5. Regresia logistică
6. K-Means
7. Motorul de predicție
8. Backtesting cronologic
9. Metrici de evaluare
10. Compararea algoritmilor
11. Interfața grafică (PySide6)
12. Vizualizare
13. Testare de integrare și finisare
14. Pachete de instalare pentru macOS și Windows
15. Cinci ligi: date, calibrare, evaluare și comparația ligilor
16. Identitate vizuală și interfață nouă, în limba română
17. Pachete și versiunea 0.2.0
18. Sezonul în desfășurare: meciurile programate, prezise de modele, și actualizarea datelor din aplicație
19. Interfață centrată pe meciuri: meciurile pe zile, clasamentul, pagina echipei și analiza modelelor
20. Pachete și versiunea 0.3.0
21. Design refăcut: suprafețe neutre cu accentul fiecărei ligi și animația schimbării lui, sigla nouă, o literă nouă, antetul cu imaginea ligii la rezoluția ecranului și ecrane pentru orice lățime
22. Interfața web: ecranele refăcute ca aplicație web într-o fereastră de desktop, peste algoritmii și serviciile Python; fereastra PySide6 scoasă
