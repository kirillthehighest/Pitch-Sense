# PitchSense

Aplicație desktop pentru analiza datelor istorice din fotbal și estimarea rezultatelor meciurilor, pentru macOS și Windows. Aplicația folosește patru algoritmi implementați de noi, fără biblioteci gata făcute: ratingul Elo, modelul Poisson, regresia logistică și K-Means.

Proiect de an la disciplina *Analiza și Proiectarea Algoritmilor* (APA), Universitatea Tehnică a Moldovei, Departamentul Ingineria Software și Automatică.
Echipa (grupa TI-251): Goroșevschi Chiril, Cuzmici Nicolae, Păstru Alina.

**Stadiu:** Faza 8, backtesting cronologic. Fazele 0–7 (planificare și arhitectură, prelucrarea datelor istorice, statisticile echipelor, ratingul Elo, modelul Poisson, regresia logistică, K-Means, motorul de predicție) au fost încheiate pe 2026-10-04. Aplicația propriu-zisă nu este încă implementată.

## Cerințe

- Python 3.14 (PySide6 6.11 nu suportă încă Python 3.15)
- macOS sau Windows

## Instalare

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

## Date

Meciurile din La Liga (Spania), sezoanele 2006/07–2025/26, preluate de pe [Football-Data.co.uk](https://www.football-data.co.uk). Fișierele originale se află în `data/raw/SP1/`. Sursa și verificările făcute la descărcare sunt descrise în [`data/raw/README.md`](data/raw/README.md).

## Baza de date

Construiește (sau reconstruiește) baza de date `data/pitchsense.db` din fișierele brute:

```bash
python -m app.data.build_database
```

Comanda verifică toate sezoanele și afișează câte meciuri a salvat din fiecare. Baza de date nu este inclusă în git, așa că rulați comanda după clonarea proiectului și după orice modificare a fișierelor din `data/raw/`.

## Documentație

- [`docs/architecture.md`](docs/architecture.md): arhitectura aplicației, fluxul datelor și deciziile tehnice.
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
