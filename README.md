# PitchSense

Aplicație desktop pentru analiza datelor istorice din fotbal și estimarea rezultatelor meciurilor, pentru macOS și Windows. Aplicația folosește patru algoritmi implementați de noi, fără biblioteci gata făcute: ratingul Elo, modelul Poisson, regresia logistică și K-Means.

Proiect de an la disciplina *Analiza și Proiectarea Algoritmilor* (APA), Universitatea Tehnică a Moldovei, Departamentul Ingineria Software și Automatică.
Echipa (grupa TI-251): Goroșevschi Chiril, Cuzmici Nicolae, Păstru Alina.

**Stadiu:** toate etapele (0–14) sunt încheiate. Fazele 0–12 (planificare și arhitectură, prelucrarea datelor istorice, statisticile echipelor, ratingul Elo, modelul Poisson, regresia logistică, K-Means, motorul de predicție, backtesting cronologic, metricile de evaluare, compararea algoritmilor, interfața grafică, vizualizarea) au fost încheiate pe 2026-10-04, iar fazele 13 (testare de integrare și finisare) și 14 (pachete de instalare pentru macOS și Windows) pe 2026-10-05. Aplicația se pornește cu `python -m app` sau din pachetele de instalare.

## Aplicația gata de instalat

Pachetele nu cer Python și conțin deja datele (baza de date și jurnalul predicțiilor).

| Sistem | Fișier | Cerințe |
|---|---|---|
| macOS | `PitchSense-0.1.0-macOS-arm64.dmg` | Mac cu procesor Apple Silicon, macOS 14 sau mai nou |
| Windows | `PitchSense-0.1.0-Windows-amd64.zip` | Windows 10 sau 11, pe 64 de biți |

**macOS:** deschideți fișierul `.dmg` și trageți `PitchSense` în `Applications`. Pachetul nu este semnat, așa că macOS blochează prima deschidere a unei copii descărcate din internet: deschideți *System Settings → Privacy & Security* și alegeți *Open Anyway* în dreptul mesajului despre PitchSense.

**Windows:** dezarhivați fișierul `.zip` și porniți `PitchSense\PitchSense.exe`. Pachetul nu este semnat, așa că Windows poate afișa „Windows protected your PC”: alegeți *More info*, apoi *Run anyway*.

Prima pornire durează până la aproximativ 30 de secunde, pentru că se pregătesc fonturile graficelor; următoarele durează aproximativ 10 secunde. Aplicația își păstrează fișierele în `~/Library/Application Support/PitchSense` (macOS) sau în `%LOCALAPPDATA%\PitchSense` (Windows); ștergerea acestui folder o readuce la starea de după instalare.

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

Meciurile din La Liga (Spania), sezoanele 2006/07–2025/26, preluate de pe [Football-Data.co.uk](https://www.football-data.co.uk). Fișierele originale se află în `data/raw/SP1/`. Sursa și verificările făcute la descărcare sunt descrise în [`data/raw/README.md`](data/raw/README.md).

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

La pornire, aplicația calculează o dată toate predicțiile istorice (aproximativ 7 secunde; bara de stare arată „Predictions ready” când au fost calculate). Filele:

- **Dashboard:** datele încărcate și rezultatele principale ale modelelor;
- **Match Prediction:** predicția unui meci jucat sau a oricăror două echipe dintr-un sezon, la o anumită dată, cu graficul probabilităților scorurilor (Poisson);
- **Team Analysis:** clasamentul și prezentarea unei echipe, la final de sezon sau la o anumită dată, evoluția ratingului ei Elo și grupurile K-Means ale sezonului;
- **Algorithm Comparison:** compararea modelelor, în tabele și în grafice (calibrarea și matricea de confuzie).

Dacă jurnalul predicțiilor lipsește sau nu poate fi citit, butonul **Run backtest** îl construiește din nou (aproximativ 8 secunde).

## Construirea pachetelor

**macOS** (pe un Mac cu Apple Silicon, cu mediul virtual activat):

```bash
python packaging/build.py
```

Comanda reconstruiește baza de date și jurnalul predicțiilor, care intră în pachet, și produce `dist/PitchSense-0.1.0-macOS-arm64.dmg`.

**Windows:** pachetul se construiește pe GitHub, cu fluxul „Windows package” (`.github/workflows/package.yml`): pe pagina *Actions* a depozitului, *Windows package → Run workflow*. Fluxul rulează toate testele pe Windows, construiește pachetul, îl verifică și îl păstrează 30 de zile ca *artifact* (`PitchSense-Windows`). Pe un calculator cu Windows se poate folosi și `python packaging/build.py`.

Orice pachet se poate verifica automat: opțiunea `--self-test` deschide fereastra fără a o afișa, folosește fiecare filă și se termină cu codul 0 dacă totul a funcționat.

```bash
dist/PitchSense.app/Contents/MacOS/PitchSense --self-test
```

Din codul sursă, aceeași verificare este `python -m app --self-test`.

## Evaluare

Rulează toate modelele cronologic pe sezoanele de evaluare și salvează jurnalul predicțiilor în `data/results/backtest_SP1.csv`:

```bash
python -m app.evaluation.backtesting
```

Calculează măsurile de evaluare (acuratețe, scor Brier, pierdere logaritmică, calibrare) pentru fiecare model:

```bash
python -m app.evaluation.evaluator
```

Compară modelele meci cu meci, pe sezoane, pe rezultate și pe tipuri de meciuri:

```bash
python -m app.evaluation.comparison
```

## Documentație

- [`docs/architecture.md`](docs/architecture.md): arhitectura aplicației, fluxul datelor și deciziile tehnice.
- [`docs/evaluation.md`](docs/evaluation.md): măsurile de evaluare și rezultatele modelelor.
- [`docs/comparison.md`](docs/comparison.md): compararea algoritmilor.
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
