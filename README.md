# PitchSense

Aplicație desktop pentru analiza datelor istorice din fotbal și estimarea rezultatelor meciurilor, pentru macOS și Windows. Aplicația folosește patru algoritmi implementați de noi, fără biblioteci gata făcute: ratingul Elo, modelul Poisson, regresia logistică și K-Means.

Proiect de an la disciplina *Analiza și Proiectarea Algoritmilor* (APA), Universitatea Tehnică a Moldovei, Departamentul Ingineria Software și Automatică.
Echipa (grupa TI-251): Goroșevschi Chiril, Cuzmici Nicolae, Păstru Alina.

**Stadiu:** etapele 0–19 sunt încheiate; versiunea publicată este 0.2.0. Etapele 18 (sezonul în desfășurare) și 19 (interfață centrată pe meciuri) au fost adăugate de echipă și încheiate pe 2026-10-15; etapa 20 (pachete și versiunea 0.3.0) este în lucru. Fazele 0–12 (planificare și arhitectură, prelucrarea datelor istorice, statisticile echipelor, ratingul Elo, modelul Poisson, regresia logistică, K-Means, motorul de predicție, backtesting cronologic, metricile de evaluare, compararea algoritmilor, interfața grafică, vizualizarea) au fost încheiate pe 2026-10-04, fazele 13 (testare de integrare și finisare), 14 (pachete de instalare pentru macOS și Windows), 15 (cinci ligi) și 16 (identitate vizuală și interfață nouă, în limba română) pe 2026-10-05, iar faza 17 (pachete și versiunea 0.2.0) pe 2026-10-06. Aplicația se pornește cu `python -m app` sau din pachetele de instalare.

## Aplicația gata de instalat

Pachetele se descarcă de pe pagina [Releases](https://github.com/kirillthehighest/Pitch-Sense/releases/latest) a depozitului (versiunea curentă: 0.3.0). Depozitul este privat, deci pagina se deschide doar pentru cei care au acces la el. Pachetele nu cer Python și conțin deja datele: baza de date cu cele cinci ligi, jurnalele predicțiilor fiecărei ligi și sezonul în desfășurare de la data construirii (butonul **Actualizează datele** îl aduce la zi).

| Sistem | Fișier | Cerințe |
|---|---|---|
| macOS | `PitchSense-0.3.0-macOS-arm64.dmg` | Mac cu procesor Apple Silicon, macOS 14 sau mai nou |
| Windows | `PitchSense-0.3.0-Windows-amd64.zip` | Windows 10 sau 11, pe 64 de biți |

**macOS:** deschideți fișierul `.dmg` și trageți `PitchSense` în `Applications`. Pachetul nu este semnat, așa că macOS blochează prima deschidere a unei copii descărcate din internet: deschideți *System Settings → Privacy & Security* și alegeți *Open Anyway* în dreptul mesajului despre PitchSense.

**Windows:** dezarhivați fișierul `.zip` și porniți `PitchSense\PitchSense.exe`. Pachetul nu este semnat, așa că Windows poate afișa „Windows protected your PC”: alegeți *More info*, apoi *Run anyway*.

Prima pornire durează până la aproximativ 30 de secunde, pentru că se pregătesc fonturile graficelor; următoarele durează aproximativ 10 secunde. Aplicația își păstrează fișierele în `~/Library/Application Support/PitchSense` (macOS) sau în `%LOCALAPPDATA%\PitchSense` (Windows); ștergerea acestui folder o readuce la starea de după instalare. După instalarea unei versiuni noi, jurnalele predicțiilor lăsate de versiunea veche sunt înlocuite la prima pornire cu cele noi; liga aleasă și echipa ta rămân.

## Cerințe (pentru codul sursă)

- Python 3.14 (PySide6 6.11 nu suportă încă Python 3.15)
- macOS sau Windows

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

## Verificare

Cu mediul virtual activat:

```bash
python -m pytest
python -m ruff check .
python -m ruff format --check .
```

Testele folosesc doar date sintetice. `tests/test_integration.py` rulează tot lanțul, de la fișierele CSV la fereastra aplicației, fără fereastră vizibilă.

## Date

Meciurile din cinci ligi, sezoanele 2006/07–2025/26 (36.197 de meciuri), preluate de pe [Football-Data.co.uk](https://www.football-data.co.uk): Premier League (`E0`), La Liga (`SP1`), Serie A (`I1`), Bundesliga (`D1`) și Ligue 1 (`F1`). Fișierele originale se află în `data/raw/<cod>/`. Sursa și verificările făcute la descărcare sunt descrise în [`data/raw/README.md`](data/raw/README.md).

### Sezonul în desfășurare

Pentru meciurile care urmează, aplicația descarcă sezonul în desfășurare (acum 2026/27): rezultatele de până acum de la Football-Data.co.uk și calendarul întregului sezon de la [openfootball/football.json](https://github.com/openfootball/football.json) (domeniu public, CC0). Descărcarea are loc doar la cerere, cu butonul **Actualizează datele** din aplicație sau cu comanda:

```bash
python -m app.data.update
```

Fișierele sunt verificate înainte să le înlocuiască pe cele vechi și sunt păstrate în `data/live/` (nu sunt incluse în git). Fără ele, aplicația arată doar sezoanele încheiate. Detalii: [`docs/architecture.md`](docs/architecture.md), secțiunea 15.

## Baza de date

Construiește (sau reconstruiește) baza de date `data/pitchsense.db` din fișierele brute:

```bash
python -m app.data.build_database
```

Comanda verifică toate sezoanele și afișează câte meciuri a salvat din fiecare. Baza de date nu este inclusă în git, așa că rulați comanda după clonarea proiectului și după orice modificare a fișierelor din `data/raw/`.

## Pornirea aplicației

Cu mediul virtual activat și baza de date construită:

```bash
python -m app
```

Liga se alege din panoul din stânga. După pornire, aplicația calculează în fundal predicțiile fiecărei ligi, întâi pe cea aleasă (aproximativ 7 secunde pe ligă; bara de stare arată „Predicțiile pentru … sunt gata”). Ultima ligă afișată este redeschisă la următoarea pornire. Ecranele, din bara de sus:

- **Meciuri:** meciurile fiecărei zile, din toate ligile, cu stemele cluburilor și probabilitățile modelului ales (implicit regresia logistică); la meciurile jucate, scorul și dacă modelul a nimerit. Un clic pe un meci deschide pagina lui: toate modelele, scorurile probabile (Poisson) și cum vin echipele. „Alt meci…” prezice oricare două echipe ale unui sezon, la o dată aleasă;
- **Clasament:** clasamentul unui sezon sau la o anumită dată, cu forma fiecărei echipe; un clic pe o echipă îi deschide pagina;
- **Echipe:** pagina unei echipe: sezonul în cifre, forma, următorul meci și ultimele rezultate, profilul K-Means, ratingul Elo și grupurile;
- **Analiză:** cum funcționează algoritmii, cum au prezis sezonul în desfășurare, compararea modelelor (tabele, calibrare, matricea de confuzie), comparația celor cinci ligi și sursele datelor și imaginilor.

Butonul auriu **Echipa ta** din dreapta sus păstrează echipa pe care o urmăriți: are cardul ei pe ecranul Meciuri, este evidențiată în liste și clasamente și aleasă din start pe ecranul Echipe.

Butonul **Actualizează datele** descarcă rezultatele și calendarul sezonului în desfășurare (câteva secunde, cu internet); restul aplicației funcționează fără internet. Panoul din stânga arată când au fost actualizate datele ultima dată.

Dacă jurnalul predicțiilor unei ligi lipsește sau nu poate fi citit, butonul **Rulează backtestul** îl construiește din nou (aproximativ 8–10 secunde pe ligă).

## Construirea pachetelor

**macOS** (pe un Mac cu Apple Silicon, cu mediul virtual activat):

```bash
python packaging/build.py
```

Comanda reconstruiește baza de date și jurnalele predicțiilor celor cinci ligi, descarcă sezonul în desfășurare (cu internet), toate intrând în pachet, desenează iconița aplicației din siglă și produce `dist/PitchSense-0.3.0-macOS-arm64.dmg`. Versiunea este scrisă într-un singur loc, `app/__init__.py`.

**Windows:** pachetul se construiește pe GitHub, cu fluxul „Windows package” (`.github/workflows/package.yml`): pe pagina *Actions* a depozitului, *Windows package → Run workflow*. Fluxul rulează toate testele pe Windows, construiește pachetul, îl verifică și îl păstrează 30 de zile ca *artifact* (`PitchSense-Windows`). Pe un calculator cu Windows se poate folosi și `python packaging/build.py`.

Orice pachet se poate verifica automat: opțiunea `--self-test` deschide fereastra fără a o afișa, folosește fiecare ecran și se termină cu codul 0 dacă totul a funcționat.

```bash
dist/PitchSense.app/Contents/MacOS/PitchSense --self-test
```

Din codul sursă, aceeași verificare este `python -m app --self-test`. Opțiunea `--update` (`python -m app --update`, sau aplicația împachetată pornită cu `--update`) face aceeași actualizare ca butonul **Actualizează datele**, fără fereastră.

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

### Imaginile

Stemele cluburilor vin de pe Wikipedia, la rezoluție mică (`tools/crests.py`, care se rulează doar ca să le reîmprospăteze). Imaginile ligilor sunt imagini promoționale DAZN, alese de echipă. Stemele și imaginile aparțin deținătorilor lor: sunt folosite doar ca să recunoști echipele și ligile și rămân în depozitul privat și în pachete.

## Documentație

- [`docs/architecture.md`](docs/architecture.md): arhitectura aplicației, fluxul datelor și deciziile tehnice.
- [`docs/evaluation.md`](docs/evaluation.md): măsurile de evaluare și rezultatele modelelor în La Liga.
- [`docs/comparison.md`](docs/comparison.md): compararea algoritmilor în La Liga.
- [`docs/leagues.md`](docs/leagues.md): comparația celor cinci ligi.
- [`docs/brand.md`](docs/brand.md): identitatea vizuală: semnul, culorile, literele și regulile interfeței.
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
