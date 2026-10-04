# Arhitectura aplicației PitchSense

Acest document descrie structura aplicației, fluxul datelor și deciziile tehnice luate în Faza 0. Se actualizează ori de câte ori structura se schimbă.

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

## 5. Formatul comun al predicției

Fiecare model care estimează rezultatul unui meci întoarce:

- numele modelului;
- probabilitățile `(p_home, p_draw, p_away)`, mereu în această ordine: victoria gazdelor, egal, victoria oaspeților. Valorile sunt nenegative, iar suma lor este 1 (cu toleranța 1e-9);
- opțional, doar pentru modelul Poisson: numărul așteptat de goluri și matricea probabilităților pentru fiecare scor.

K-Means nu prezice rezultatul meciului. El întoarce grupuri (clustere) de echipe cu profiluri statistice asemănătoare.

## 6. Backtesting cronologic

Meciurile sunt parcurse în ordinea datelor. Pentru fiecare zi de joc D:

1. modelele care se antrenează (regresia logistică, parametrii modelului Poisson) sunt reantrenate, după un program documentat, doar pe meciurile dinaintea zilei D;
2. fiecare model prezice toate meciurile din ziua D, iar predicțiile sunt salvate;
3. abia apoi se dezvăluie rezultatele din ziua D și se actualizează modelele cu stare (ratingurile Elo).

Metricile se calculează din jurnalul predicțiilor salvate, în aceleași condiții pentru toate modelele.

## 7. Setul de date și perioadele

Sursa datelor este Football-Data.co.uk: La Liga (`SP1`), 20 de sezoane încheiate, 2006/07–2025/26 (7.600 de meciuri).

| Perioadă | Rol |
|---|---|
| 2006/07 | Încălzire: construiește ratingurile și istoricul; nu este evaluată. |
| 2007/08–2009/10 | Calibrare: se aleg hiperparametrii; rezultatele nu sunt raportate. |
| 2010/11–2025/26 | Evaluarea raportată: 16 sezoane, 6.080 de meciuri. |

## 8. Tehnologii

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

## 9. Decizii tehnice

| Decizie | Motiv |
|---|---|
| Python 3.14 | Este cea mai nouă versiune suportată de PySide6 6.11, care cere Python < 3.15. |
| `PySide6-Essentials` în locul pachetului complet `PySide6` | Conține modulele Qt de care avem nevoie (QtCore, QtGui, QtWidgets). Pachetul complet adaugă circa 330 MB de module nefolosite (web, 3D, multimedia), iar graficele sunt realizate cu matplotlib. |
| `pyproject.toml` cu versiuni fixe (`==`), mediu virtual `.venv` și `pip` | Aceleași versiuni pe macOS și Windows. Actualizările se fac intenționat și sunt urmate de rularea tuturor testelor. |
| ruff, fără verificator static de tipuri | Un singur instrument rapid pentru stil și erori frecvente. Adnotările de tip rămân obligatorii. |
| Avertismentele sunt tratate ca erori în teste | Schimbările de API din pandas 3 și NumPy 2 sunt observate imediat, nu ignorate. |
| Interfața și codul în engleză; documentația și raportul în română | Decizia echipei. |
