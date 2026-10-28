# Date brute

Acestea sunt fișierele originale, nemodificate. Nu se editează manual; corecțiile se fac în etapa de prelucrare a datelor (`app/data/`).

Aici stau doar sezoanele încheiate. Sezonul în desfășurare este descărcat separat în `data/live/`: de aplicație, singură, la câteva ore, sau la cerere (`python -m app.data.update`; `docs/architecture.md`, secțiunile 15 și 20). Coloana `Time` dă ora în ora Marii Britanii (verificat pe 2026-10-28: pentru La Liga, Serie A, Bundesliga și Ligue 1 este cu exact o oră înaintea orei din calendarul openfootball, care este ora locală); aplicația o mută în ora locală a ligii.

| | |
|---|---|
| Sursa | Football-Data.co.uk, https://www.football-data.co.uk/data.php |
| Sezoane | 2006/07–2025/26 (20 de sezoane încheiate pentru fiecare ligă) |
| Adresa fișierelor | `https://www.football-data.co.uk/mmz4281/<aaaa>/<cod>.csv` (de exemplu `0607` = 2006/07; adresa trimite la același fișier pe `football-data.co.uk`) |
| Salvate ca | `<cod>/<sezon>.csv` (de exemplu `SP1/2006-07.csv`) |
| Dimensiune | 100 de fișiere, circa 11,7 MB |

| Ligă | Cod (`Div`) | Pagina sursei | Descărcate | Dimensiune |
|---|---|---|---|---|
| Premier League | `E0` | https://www.football-data.co.uk/englandm.php | 2026-10-05 | circa 2,5 MB |
| La Liga | `SP1` | https://www.football-data.co.uk/spainm.php | 2026-10-04 | circa 2,5 MB |
| Serie A | `I1` | https://www.football-data.co.uk/italym.php | 2026-10-05 | circa 2,4 MB |
| Bundesliga | `D1` | https://www.football-data.co.uk/germanym.php | 2026-10-05 | circa 2,0 MB |
| Ligue 1 | `F1` | https://www.football-data.co.uk/francem.php | 2026-10-05 | circa 2,3 MB |

Verificări la descărcare: fiecare sezon este un campionat complet tur-retur, fără meciuri duplicate, rezultate care contrazic scorul sau valori lipsă în câmpurile principale. Premier League, La Liga și Serie A au 20 de echipe și 380 de meciuri în fiecare sezon; Bundesliga are 18 echipe și 306 meciuri.

Particularități, verificate pe fișiere:

- **Ligue 1** are 20 de echipe până în 2022/23 și 18 din 2023/24. Sezonul **2019/20** are doar 279 de meciuri: a fost oprit din cauza pandemiei de COVID-19, iar clasamentul a fost stabilit după punctele pe meci.
- **Serie A 2019/20** s-a încheiat pe 2 august 2020.
- **Ligue 1 2006/07** nu are statistici de șuturi pentru niciun meci. Statisticile lipsesc și la câteva meciuri din alte sezoane: Serie A 2012/13 și 2014/15 (câte 1), Bundesliga 2024/25 (1), Ligue 1 2011/12 (2) și 2016/17 (1).
- Unele fișiere încep cu un marcaj BOM: La Liga, Serie A, Bundesliga și Ligue 1 din 2024/25, Premier League 2021/22 și din 2024/25.
- Numărul de coloane variază între 61 și 132, după coloanele cu cote.

Football-Data.co.uk corectează uneori fișierele vechi. Pentru ca rezultatele să rămână reproductibile, descărcați din nou fișierele doar intenționat și notați aici noua dată.
