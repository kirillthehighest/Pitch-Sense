# Identitatea vizuală PitchSense

Acest document descrie sigla, culorile, literele și regulile interfeței PitchSense și explică de ce a fost ales fiecare element. Identitatea a fost creată în Faza 16 și refăcută în Faza 21. Publicul aplicației sunt colegii și profesorii care urmăresc fotbalul. Aplicația trebuie să arate ca aplicațiile de fotbal pe care le folosesc deja: LiveScore, OneFootball, site-urile ligilor. Asta înseamnă:

- o temă întunecată;
- titluri condensate, scrise cu majuscule;
- carduri de meci;
- un singur accent de culoare care arată unde să te uiți.

**Faza 16** a trecut prin trei încercări de siglă:

1. un semn neutru, pe o temă deschisă la culoare;
2. o stemă de club pe o temă întunecată, pe care echipa a găsit-o prea apropiată de stema Barcelonei;
3. monograma PS albă, geometrică, pe un pătrat albastru–grena.

**Faza 21** a pornit de la cererea echipei de a lucra mai mult la design. Fiecare ligă primește gama ei de culori, iar schimbarea ligii schimbă toate culorile aplicației, cu o animație. Echipa a ales, din variantele propuse:

- stilul „sticlă întunecată”, inspirat de aplicațiile Sportia, AI Football și de un panou FIFA;
- extinderea estompată a imaginilor ligilor;
- culorile după identitatea fiecărei ligi.

Sigla a fost refăcută în mai mulți pași:

1. Prima serie de monograme, pe pătrate rotunjite, semăna cu iconița Adobe Photoshop.
2. Echipa a cerut un semn „îndrăzneț”, cu litere ascuțite, ca la LiveScore.
3. A respins și o a doua serie, apoi conceptele fără litere: literele trebuie să rămână baza siglei.
4. Dintre patru concepte cu litere a ales tăietura (L2). Dintre finisajele ei a ales varianta în două culori, care este sigla de acum.

## 1. Conceptul: PS tăiat

Sigla este formată din **literele P și S, înclinate și foarte groase, tăiate de o bară oblică** care urcă spre dreapta. Partea de deasupra tăieturii este albă, partea de dedesubt are culoarea de accent a ligii afișate. Sigla nu are pătrat, contur, minge sau scut: doar literele și tăietura.

- **Literele înclinate** dau senzația de viteză din grafica sportivă: LiveScore, tricourile și numerele de pe ele.
- **Tăietura** este gestul semnului: o diagonală ca o pasă sau ca linia unei tactici, care împarte sigla în două, cum se împarte un meci în două reprize.
- **Cele două culori** leagă sigla de liga afișată. Partea de jos e verde în Premier League, portocalie în La Liga, albastru-cyan în Serie A, roșie în Bundesliga și verde-lime în Ligue 1.

Din stemele cluburilor sau din siglele ligilor nu apare nimic.

## 2. Formele

### 2.1. Geometria siglei

Sigla se desenează cu QPainter (`paint_logo` și `logo_parts` din `app/ui/brand.py`, singura sursă a desenului):

| Element | Desen |
|---|---|
| Literele | „PS” scris cu Kanit Black Italic și transformat în contur; contururile care se suprapun sunt unite, deci literele se desenează ca o singură formă |
| Așezarea | literele umplu dreptunghiul primit, păstrându-și proporțiile, și sunt centrate în el |
| Tăietura | o bandă înclinată la 15°, care urcă spre dreapta și trece prin literele la 56% din înălțimea lor, numărând de sus; lățimea ei este 9% din înălțimea literelor și rămâne goală (transparentă) |
| Culorile | deasupra tăieturii alb pur `#FFFFFF`, dedesubt accentul ligii (secțiunea 3) |

**Mărimi mici.** Sigla rămâne aceeași la toate mărimile, de la 1024 la 16 pixeli. Literele sunt groase, așa că tăietura rămâne vizibilă și la 16 pixeli.

**Spațiul liber.** În jurul siglei se lasă liber cel puțin cât lățimea tăieturii. Sigla nu se rotește, nu se deformează și nu primește umbră.

### 2.2. Sigla cu numele

Lângă siglă, numele se scrie **PITCHSENSE** cu Kanit ExtraBold Italic, la 62% din înălțimea siglei: „PITCH” alb și „SENSE” în accentul ligii (`Lockup` din `app/ui/brand.py`). Într-o fereastră îngustă (sub 1180 px) rămâne doar sigla, iar numele apare la trecerea mausului. Sub bara de sus se întinde o linie subțire, de la o lumină a ligii la cealaltă.

### 2.3. Iconița aplicației

Iconița aplicației pune sigla pe un pătrat cu colțurile rotunjite (raza de 23% din latură, ca iconițele macOS). Pătratul are un gradient din noaptea ligii și e luminat din colțul de jos de lumina ei principală (`paint_icon`, `icon_image`). Aplicația are imagini pentru mărimile 16, 24, 32, 48, 64, 128, 256, 512 și 1024 de pixeli (`app_icon`). Când utilizatorul schimbă liga, se schimbă și iconița ferestrei.

Pentru pachete, `packaging/icons.py` desenează iconița în culorile La Ligii, liga implicită, și o salvează la fiecare construire:

- în `PitchSense.icns` (macOS, unsprezece imagini de la 16 la 1024 de pixeli);
- în `PitchSense.ico` (Windows, șapte imagini de la 16 la 256 de pixeli).

Scriptul se oprește dacă fontul Kanit nu se încarcă, pentru că atunci sigla ar fi desenată cu alt font.

### 2.4. Steagurile și ecusoanele

- **Ligile** au steagul rotund al țării lor, ca în listele LiveScore și OneFootball: Anglia, Spania, Italia, Germania și Franța (`flag_pixmap`). Steagurile țărilor nu aparțin nimănui. Siglele ligilor sunt mărci înregistrate și nu sunt folosite.
- **Echipele** au stema clubului, din Faza 19, la decizia echipei. Stemele vin de pe Wikipedia, la cel mult 128 px (`app/ui/assets/crests/`, cu sursa fiecăreia în `sources.json`). Sunt mărci ale cluburilor, folosite doar ca să recunoști echipele, într-un proiect privat.
  - O stemă aproape în întregime întunecată (Juventus, Tottenham, Derby) stă pe un disc deschis (`#E9EDF5`), altfel ar dispărea pe fundalul închis.
  - O echipă fără stemă are un ecuson rotund cu trei litere (BAR, RMA, MUN; `team_abbreviation`).
  - Echipa ta are un inel în accentul ligii în jurul stemei.
- **Ligile** au în antet o imagine promoțională cu jucătorii lor, aleasă de echipă (sursa, DAZN, e scrisă în colțul antetului). Drepturile aparțin deținătorilor; imaginile rămân în proiectul privat (`docs/architecture.md`, secțiunea 16.5).

## 3. Culorile

### 3.1. O gamă pentru fiecare ligă

Fiecare ligă are paleta ei, după identitatea ei vizuală (`app/ui/themes.py`, clasa `Theme`). Toată interfața ia paleta ligii afișate:

- suprafețele: fundalul, cardurile, bara de sus, panoul ligilor;
- accentul: ecranul ales, butonul principal, legăturile, echipa ta;
- luminile din fundal, antetul, sigla și iconița.

| Ligă | Inspirație | Noapte | Card | Text secundar | Accent | Lumini |
|---|---|---|---|---|---|---|
| Premier League | mov, magenta și verdele ligii | `#12051F` | `#231236` | `#BBAAD2` | `#00FF85` | `#E90052`, `#7B2FF7` |
| La Liga | roșul și portocaliul ligii | `#160705` | `#2A110D` | `#D2B1A7` | `#FF8A3D` | `#FF3B30`, `#FF9500` |
| Serie A | albastrul ligii | `#040B1D` | `#0C1C3C` | `#A8BADB` | `#3DDCFF` | `#1F5BFF`, `#00C8FF` |
| Bundesliga | roșul ligii | `#150406` | `#290B0F` | `#D7ACB2` | `#FF5566` | `#D20515`, `#FF7A85` |
| Ligue 1 | bleumarinul nopții, verdele-lime al ligii | `#05080F` | `#0E1526` | `#AAB5CC` | `#D4FF3D` | `#2A4BFF`, `#00A3FF` |

Fiecare paletă mai are:

- un fundal, între noapte și card;
- două suprafețe mai deschise (capete de tabele, câmpuri, trecerea cu mausul; butoane apăsate);
- o culoare de linie;
- un text aproape alb, cu o urmă din culoarea ligii;
- un text șters, doar pentru controalele dezactivate;
- textul de pe accent (noaptea ligii);
- accentul la trecerea mausului (accentul luminat cu 18%).

Rândul echipei tale din tabele are accentul la 16% peste card.

**Ce nu se schimbă.** Unele culori rămân aceleași în toate ligile, pentru că au fost validate pentru daltoniști (`app/visualization/palette.py`):

- culorile rezultatelor: barele de probabilitate (gazde `#2B63D9`, egal `#8790A6`, oaspeți `#C2185B`), pătrățelele de formă, bifa și crucea;
- culorile modelelor din grafice.

**De ce întunecat.** Aplicațiile de fotbal moderne sunt întunecate, iar tema întunecată pune în valoare culorile, imaginile și cifrele mari. Am urmat regulile obișnuite ale unei teme întunecate:

- o noapte colorată în locul negrului pur;
- un text aproape alb în locul albului pur, ca textul să nu „ardă”;
- adâncimea se arată prin suprafețe tot mai deschise, nu prin umbre.

### 3.2. Contrastul

Raporturile de contrast sunt calculate după WCAG 2.1 și verificate de `tests/test_themes.py` pentru fiecare paletă. Pragurile:

- textul are cel puțin 7 : 1;
- textul secundar și accentul folosit ca text au cel puțin 4,5 : 1;
- textul de pe accent are cel puțin 4,5 : 1.

Contrastul este verificat pe toate suprafețele, inclusiv pe cardurile de sticlă așezate peste cel mai luminos punct al luminilor din fundal. Tabelul dă cele mai mici valori găsite:

| Ligă | Text | Text secundar | Accent ca text | Text pe accent | Text pe rândul echipei tale | Alb pe antetul meciului |
|---|---|---|---|---|---|---|
| Premier League | 12,33 | 6,39 | 11,66 | 14,66 | 11,12 | 9,66 |
| La Liga | 12,99 | 7,11 | 6,85 | 8,39 | 12,32 | 5,93 |
| Serie A | 11,55 | 6,40 | 9,03 | 12,03 | 10,71 | 5,28 |
| Bundesliga | 13,65 | 7,44 | 5,38 | 6,41 | 13,29 | 6,65 |
| Ligue 1 | 13,21 | 7,00 | 14,18 | 17,34 | 10,95 | 6,97 |

Accentul Bundesligii a fost luminat de la `#FF4255` la `#FF5566`: folosit ca text, avea doar 4,4 : 1. Culorile rezultatelor au aceleași contraste ca în Faza 16, toate peste 4,5 : 1: alb pe gazde, oaspeți, victorie și înfrângere, noapte pe egal.

## 4. Literele

- **Kanit** (Cadson Demak, licența SIL Open Font License 1.1) se folosește doar pentru siglă (Black Italic) și pentru numele de lângă ea (ExtraBold Italic). Este o literă geometrică, grea, cu o înclinare ascuțită, ca literele aplicațiilor de scoruri. Am încercat și Unbounded și Chakra Petch; echipa a ales sigla desenată cu Kanit.
- **Barlow Condensed** (Jeremy Tribby, SIL Open Font License 1.1) se folosește pentru titluri, cifre mari, scor, navigare și sub-file, aproape mereu cu majuscule. Este o literă condensată, ca titlurile din presa sportivă: încape mult text pe puțin loc și se citește dintr-o privire. Aplicația include grosimile 500, 600, 700 și 800.
- **Libre Franklin** (Impallari Type, SIL Open Font License 1.1) se folosește pentru textul obișnuit, tabele și explicații. Aplicația include grosimile 400, 500, 600, 700 și 800.

Toate trei au diacriticele românești corecte (ș și ț cu virgulă dedesubt). Fișierele și licențele (`OFL-Kanit.txt`, `OFL-BarlowCondensed.txt`, `OFL-LibreFranklin.txt`) sunt în `app/ui/assets/fonts/`. Qt le înregistrează la pornire (`load_fonts` din `app/ui/theme.py`), iar matplotlib la primul grafic. Dacă un font nu se încarcă, aplicația folosește un font al sistemului, iar autoverificarea raportează problema.

| Rol | Literă și mărime |
|---|---|
| titlul ecranului | Barlow Condensed, 50 px, 800 |
| cifrele mari | Barlow Condensed, 46 px, 700 |
| scorul | Barlow Condensed, 60 px, 800 |
| numele echipelor din cardul de meci | Barlow Condensed, 26 px, 700 |
| navigarea | Barlow Condensed, 17 px, 700 |
| titlurile secțiunilor | Barlow Condensed, 22 px, 700 |
| textul | Libre Franklin, 14 px |
| textul secundar | Libre Franklin, 13 px |
| etichetele scrise cu majuscule | Libre Franklin, 12 px, 700 |

## 5. Interfața

### 5.1. Stilul: sticlă întunecată

Interfața urmează aplicațiile date ca exemplu de echipă (Sportia, AI Football, aplicația cu verde-lime, panoul FIFA):

- **Fundalul** ferestrei este noaptea ligii, cu cele două lumini ale ei, slabe, în colțul din stânga sus și în cel din dreapta jos (`Backdrop`).
- **Cardurile** sunt de sticlă: culoarea cardului la 74% opacitate, o margine albă la 8% și colțurile rotunjite cu raza de 20 px.
- **Butoanele, navigarea, jetoanele zilelor, filtrele și sub-filele** sunt pastile (raza de 18 px). Cea aleasă este plină cu accentul, cu text în noaptea ligii.
- **Antetul** fiecărui ecran este și el un card rotunjit (230 px înălțime, raza de 22 px), cu marginile ferestrei în jur.

### 5.2. Așezarea

- **Bara de sus** are:
  - sigla cu numele;
  - cele patru ecrane (Meciuri, Clasament, Echipe, Analiză), cel ales ca pastilă în accentul ligii;
  - în dreapta, butonul „Actualizează datele” și butonul „Echipa ta”, conturat cu accentul.

  Sub bară se întinde linia luminilor ligii.
- **Panoul din stânga** are titlul „COMPETIȚII” și cele cinci ligi, fiecare cu steagul și țara ei. Liga aleasă este nuanțată cu accentul și are o linie în accent în stânga. Jos sunt versiunea, sursele și data actualizării.
- **Antetul** pune imaginea ligii în dreapta, clară. Spre stânga, imaginea se topește într-o copie estompată a ei, care umple tot antetul (secțiunea 5.4). Peste imagine apar:
  - liga (cu steag, în accent, cu majuscule);
  - titlul ecranului cu litere mari;
  - o explicație, care rămâne mereu la stânga imaginii clare, ca să nu treacă peste jucători;
  - sursa imaginii, în colț.

| Ecran | Ce arată |
|---|---|
| Meciuri | banda de zile (șapte jetoane-pastilă, ziua aleasă plină cu accentul), ziua aleasă, filtrele și modelul. Meciurile zilei sunt grupate pe ligă, fiecare ligă pe un card de sticlă cu steag. Fiecare rând de meci arată ora (sau „Final”, „Amânat”), stemele și numele, scorul pe o pastilă și cele trei probabilități ale modelului ales, tot ca pastile. Cea mai mare probabilitate e plină cu culoarea rezultatului, iar la meciurile jucate poartă bifa sau crucea. În dreapta: cardul echipei tale și începutul clasamentului. |
| Pagina meciului | cardul meciului în culorile ligii (noaptea ei, cele două lumini, liniile terenului), cu stemele mari, scorul sau „VS” și starea; barele celor trei modele, fiecare cu o frază simplă; cum vin echipele; scorurile probabile și harta lor |
| Clasament | tabelul ligii cu stemele și ultimele cinci rezultate |
| Echipe | banda echipei în culorile ligii, cu stema mare; șase cifre mari; forma; meciurile echipei; profilul K-Means; ratingul Elo și grupurile |
| Analiză | explicațiile algoritmilor, sezonul curent, măsurile de evaluare, cele cinci carduri de ligă și sursele |

**Colțurile din Meciuri.** În Faza 19, capul fiecărei ligi și fundalul unui rând la trecerea mausului erau dreptunghiuri. Ieșeau din colțurile rotunjite ale cardului, iar ultimul rând își trăgea linia peste ele. Din Faza 21, cardul ligii este desenat, nu stilizat (`LeagueGroup`):

- banda capului e tăiată după colțurile cardului;
- rândul de sub maus are propriul fundal rotunjit, în interiorul cardului;
- liniile dintre rânduri nu ating marginile;
- ultimul rând nu mai are linie.

### 5.3. Schimbarea ligii

Când utilizatorul alege altă ligă, fereastra trece la paleta ei:

1. Aplicația păstrează o imagine a ferestrei de dinainte.
2. Redesenează fereastra în culorile noii ligi.
3. Acoperă fereastra cu imaginea veche.
4. Un cerc pornește din colțul din stânga sus și deschide imaginea veche până trece de celelalte trei colțuri, în 0,8 s, cu o mișcare care încetinește spre final (`app/ui/transition.py`).

Marginea cercului este făcută din valuri, ca în schimbarea culorilor din Material You („Monet”) de pe Android:

- sunt două valuri, de lungimi diferite, care se mișcă în sensuri opuse; între două creste ale celui principal sunt 120 px;
- sunt înalte de 18 px la pornire și se liniștesc la 4 px pe măsură ce cercul crește;
- în urma marginii vin trei unde mai slabe, în accentul noii ligi.

Imaginea veche lasă clicurile să treacă, deci fereastra se poate folosi în timpul animației. O fereastră care nu este pe ecran (testele, autoverificarea) se schimbă fără animație.

Ca schimbarea să înceapă repede, aplicația restilizează doar fereastra, nu toată aplicația. Cu toate ecranele construite, restilizarea durează 0,15–0,3 s în loc de 0,6–0,8 s. Graficele de pe ecranele ascunse se redesenează abia când sunt deschise.

### 5.4. Imaginile ligilor

Imaginile DAZN sunt late și au jucătorii în dreapta. Pe ferestrele late nu acopereau tot antetul. Din Faza 21, antetul se umple astfel, fără inteligență artificială și fără imagini inventate:

1. **Copia estompată.** Imaginea e micșorată la 48 px lățime și mărită înapoi în doi pași, ceea ce o estompează. Copia, la 55% opacitate, acoperă tot antetul.
2. **Imaginea clară.** Ocupă dreapta antetului: cel mult 60% din lățime și cel mult 820 px, ca o fereastră foarte lată să nu taie capetele. Marginea ei din stânga devine treptat transparentă, pe 38% din lățimea ei, așa că se topește în copia estompată fără o linie vizibilă.
3. **Voalul.** Un voal din noaptea ligii, dinspre stânga, păstrează titlul lizibil.

### 5.5. O fereastră de orice lățime

Lățimea minimă a ferestrei a coborât de la 1180 la 1024 px. Niciun ecran nu mai are bară de derulare orizontală, la nicio lățime; verificarea s-a făcut la 1024, 1180, 1280, 1440 și 1920 px.

| Când e mai îngust decât | Ce se schimbă |
|---|---|
| 1280 px (fereastra) | panoul ligilor păstrează doar steagurile (76 px); numele ligii apare la trecerea mausului |
| 1180 px (fereastra) | din siglă rămâne doar semnul, fără nume |
| 980 px (conținutul din Meciuri) | cardul echipei tale și clasamentul trec sub lista meciurilor, pe toată lățimea |
| 720 px (lista din Meciuri) | alegerea modelului trece sub filtre |
| 560 px (un rând de meci) | rândul pune echipele pe un rând și probabilitățile dedesubt |
| 1000 px (conținutul din Echipe) | cardurile Forma, Meciurile echipei și Profilul K-Means trec unul sub altul |
| lățimea unei coloane | cele șase cifre ale echipei (cel puțin 128 px fiecare) și cele cinci carduri de ligă (cel puțin 210 px) trec pe rândul următor |

Piesele care fac asta sunt în `app/ui/widgets.py`:

- `ResponsiveBox` pune piesele alături sau una sub alta;
- `ReflowGrid` le așază pe atâtea coloane câte încap.

### 5.6. Echipa ta

Butonul „Echipa ta” deschide o fereastră în care utilizatorul alege o ligă și o echipă din ultimul sezon. Alegerea este păstrată între porniri, împreună cu ultima ligă afișată, în `preferences.json`, în folderul utilizatorului (`app/services/preferences.py`). Un fișier lipsă sau deteriorat nu oprește aplicația.

Echipa aleasă:

- are cardul ei pe ecranul Meciuri, conturat cu accentul (forma, următorul meci, ultimul rezultat);
- are numele în accent în lista meciurilor, rândul nuanțat în clasamente și inelul în jurul stemei;
- este aleasă din start pe ecranul Echipe.

Dacă echipa joacă în altă ligă decât cea afișată, aplicația trece la liga ei.

### 5.7. Limba și scrierea numerelor

Interfața este în limba română; codul și comentariile rămân în engleză. Tot textul afișat trece printr-un singur loc (`app/services/formatting.py` și `labels.py`):

- zecimale cu virgulă: 0,5776 și 53,4%;
- punct între mii: 7.600;
- semnul minus adevărat: −0,0073;
- datele ca zi.lună.an: 26.10.2025;
- sezoanele ca 2006/07;
- regula lui „de”: 1 meci, 19 meciuri, 20 de meciuri, 101 meciuri.

Mesajele tehnice ale erorilor rămân în engleză, dar sunt precedate de o explicație în română.

### 5.8. Componentele

Componentele folosesc stilul Qt Fusion și o paletă Qt și o foaie de stil generate din paleta ligii (`style_sheet` și `qt_palette` din `app/ui/theme.py`), deci arată la fel pe macOS și pe Windows. Elementele sunt stilizate după rol, nu unul câte unul.

Piesele desenate citesc paleta ligii afișate de fiecare dată când se desenează (`current_theme`): antetul, cardurile de ligă, cardurile meciului și ale echipei, cifrele mari, barele de probabilitate, pătrățelele de formă și butoanele ligilor.

- **Tabelele** nu au linii de grilă și stau direct pe sticla cardului. Au rânduri de 36 px și capete rotunjite. Numerele sunt aliniate la dreapta. Liniuța „–” marchează o valoare care nu există.
- **Pătrățelele de formă** au litera rezultatului (V, E, Î). Culoarea doar o repetă, deci rezultatul se citește și de daltoniști.
- **Bifa și crucea** de pe meciurile jucate urmează aceeași regulă: forma spune dacă predicția s-a nimerit, culoarea doar o repetă.
- **Jetoanele zilelor fără meciuri** nu au fundal și au textul secundar: se pot alege și trebuie să se poată citi.

## 6. Graficele

Graficele au fundal transparent: stau pe sticla cardului, în culorile oricărei ligi (`ChartView` și `on_surface` din `charts.py`). Au text deschis, titluri cu Barlow Condensed și grile subțiri. Fiecare culoare are un singur rol:

| Rol | Culori | Regulă |
|---|---|---|
| Identitatea modelelor | Elo `#4D8DFF`, Poisson `#EF5A6F`, regresie logistică `#00A3A8`; referința `#8E929C`, punctată | fiecare model are mereu aceeași culoare, pe toate graficele și în toate ligile |
| Grupurile K-Means (ordonate după putere) | `#D2E2FF`, `#8EB4FF`, `#5585F0`, `#3A63C9` | un singur albastru, de la luminos (elita) la adânc (slabă peste tot) |
| Mărimi (probabilități, număr de meciuri) | albastru în șase repere, de la `#1C2A52` la `#DCE8FF` | mai luminos înseamnă mai mult |
| Avantajul gazdelor | celelalte sezoane `#4D8DFF`, 2020/21 `#EF5A6F` | o pereche validată |
| Evidențierea | accentul ligii | un singur lucru: sezonul ales (Elo), echipa aleasă (grupuri) |

Graficele se construiesc cu auriul Fazei 16 pentru evidențiere și cu culoarea cardului din `palette.py` pentru inelele marcajelor. La afișare, `on_surface` înlocuiește aceste două culori cu accentul și cu cardul ligii afișate. La fiecare schimbare a ligii, le înlocuiește din nou.

**Validarea culorilor modelelor** (rularea din 2026-10-05, în modul întunecat):

- Cele trei culori ale modelelor trec verificările pentru linii care se pot întâlni. Cea mai mică distanță pentru daltonism este 11,3, la perechea Poisson–regresie logistică (pragul este 8).
- Barele cardului de meci sunt doi poli, albastru și grena, în jurul unui gri neutru; distanța cea mai mică pentru daltonism este 12,9.

**Desen.** Liniile au 2 px, iar marcajele au un inel de culoarea cardului. Celulele hărților de căldură sunt despărțite de spații de 2 px. Gradațiile axelor sunt la distanțe de 1, 2 sau 5 unități, cu virgulă zecimală.

## 7. Fișierele

| Fișier | Conține |
|---|---|
| `app/ui/themes.py` | paletele celor cinci ligi și paleta afișată |
| `app/visualization/palette.py` | culorile care nu se schimbă (rezultate, modele, grupuri, grafice) |
| `app/ui/brand.py` | sigla tăiată, iconița, sigla cu numele, steagurile, ecusoanele, stemele, imaginile ligilor |
| `app/ui/theme.py` | fonturile, paleta Qt și foaia de stil, generate din paleta unei ligi |
| `app/ui/transition.py` | schimbarea culorilor: cercul cu valuri |
| `app/ui/widgets.py` | piesele desenate ale interfeței, fundalul, antetul cu imaginea estompată, `ResponsiveBox`, `ReflowGrid` |
| `app/ui/match_widgets.py` | banda de zile, rândul de meci, capetele coloanelor de probabilități, bifa și crucea |
| `app/ui/assets/fonts/` | Kanit (două grosimi), Barlow Condensed (patru), Libre Franklin (cinci) și licențele |
| `app/ui/assets/crests/`, `app/ui/assets/leagues/` | stemele și imaginile ligilor, cu sursele lor |
| `app/ui/assets/icons/` | săgeata listelor și bifa |

## 8. Verificare

- `tests/test_brand.py` verifică sigla, iconița, steagurile, ecusoanele și fonturile:
  - tăietura împarte literele în două părți care nu se ating, fără nimic pe mijloc, și urcă spre dreapta;
  - sigla umple dreptunghiul primit și este centrată;
  - în fiecare ligă, sigla are doar alb (deasupra) și accentul ligii (dedesubt), fără pătrat;
  - „PITCH” e alb și „SENSE” e în accent; varianta îngustă nu are nume;
  - iconița are culorile fiecărei ligi și toate mărimile ei;
  - steagurile au culorile țărilor, iar inelul echipei tale e în accent;
  - toate cele trei fonturi se încarcă și au diacriticele românești.
- `tests/test_themes.py` verifică:
  - că fiecare ligă are paleta ei;
  - contrastele din secțiunea 3.2, inclusiv sticla peste lumini și antetele meciurilor;
  - că foaia de stil a fiecărei ligi folosește doar accentul ei.
- `tests/test_transition.py` verifică:
  - cercul crește până trece de colțul cel mai îndepărtat;
  - valurile se liniștesc, urcă și coboară de-a lungul marginii și se mișcă în timp;
  - marginea merge de la marginea de sus la cea din stânga;
  - imaginea veche se micșorează de la toată fereastra la nimic;
  - acoperirea lasă clicurile să treacă și dispare la final.
- `tests/test_ui.py` verifică:
  - schimbarea culorilor ferestrei la alegerea ligii, cu sau fără animație;
  - o schimbare întreruptă de alta;
  - fereastra îngustă (doar steagurile, doar semnul);
  - că niciun ecran nu se derulează în lateral la 1024, 1280 și 1440 px;
  - `ResponsiveBox`, `ReflowGrid`, rândul de meci îngust și ultimul rând al unei ligi;
  - explicația antetului, care ocolește imaginea;
  - graficul ascuns, redesenat la deschidere.
- `tests/test_charts.py` verifică trecerea unui grafic pe cardul altei ligi.
- `tests/test_icons.py` verifică faptul că iconița pachetelor este sigla în culorile La Ligii.
- Autoverificarea (`python -m app --self-test`, 25 de verificări) verifică și culorile ligii, și valul.
- Pe 2026-10-15, ecranele au fost desenate cu datele reale și verificate vizual: în toate cele cinci ligi, la cinci lățimi, iar animația în mai multe momente ale ei.

## 9. Limitări

- Interfața are doar tema întunecată, și când sistemul folosește modul luminos.
- Pachetele au iconița în culorile La Ligii, pentru că sistemul o citește din pachet înainte ca aplicația să pornească. Fereastra ia apoi culorile ligii afișate.
- Mesajele de la pornire, afișate înainte să existe fereastra, și indiciile de la trecerea mausului au culorile La Ligii.
- Stemele sunt mărci ale cluburilor. Sunt incluse doar în depozitul privat și în pachete, pentru recunoașterea echipelor, și nu trebuie publicate. Imaginile ligilor (DAZN) aparțin deținătorilor lor și, ca stemele, nu se publică.
