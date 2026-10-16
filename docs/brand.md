# Identitatea vizuală PitchSense

Acest document descrie sigla, culorile, literele și regulile interfeței PitchSense și explică de ce a fost ales fiecare element. Identitatea a fost creată în Faza 16 și refăcută în Faza 21. Publicul aplicației sunt colegii și profesorii care urmăresc fotbalul. Aplicația trebuie să arate ca aplicațiile de fotbal pe care le folosesc deja. Referințele alese de echipă sunt:

- aplicațiile Sportia, AI Football și o aplicație cu verde-lime;
- un panou FIFA;
- LiveScore, OneFootball și site-ul FC Barcelona.

**Faza 16** a trecut prin trei încercări de siglă:

1. un semn neutru, pe o temă deschisă la culoare;
2. o stemă de club pe o temă întunecată, pe care echipa a găsit-o prea apropiată de stema Barcelonei;
3. monograma PS albă, geometrică, pe un pătrat albastru–grena.

**Faza 21** a pornit de la cererea echipei de a lucra mai mult la design: fiecare ligă primește gama ei de culori, iar schimbarea ligii schimbă toate culorile aplicației, cu o animație. Faza a avut două versiuni.

**Prima versiune** a fost „sticlă întunecată”:

- suprafețele colorate în nuanța fiecărei ligi;
- lumini difuze în fundal;
- carduri translucide;
- o copie estompată a imaginii ligii în antet.

Echipa a respins-o, cu patru motive:

- animația sacada;
- imaginile își pierduseră calitatea;
- designul nu arăta ca un produs de calitate, ca în referințe, ci ca unul făcut în grabă;
- culorile, deși alese bine, păreau toxice în aplicație.

Cauzele au fost găsite și sunt descrise în secțiunile 5.3 și 5.4. Pe scurt:

- suprafețele colorate și luminile;
- imaginea desenată la jumătate din rezoluție pe ecranele Retina;
- o animație care redesena toată fereastra la fiecare cadru.

**A doua versiune**, cea de acum, urmează referințele mai îndeaproape:

- suprafețe neutre, aproape negre, aceleași pentru toate ligile;
- culoarea ligii doar acolo unde contează;
- carduri plate, cu spații generoase;
- pastile pentru tot ce se alege;
- o literă geometrică, scrisă normal, nu cu majuscule peste tot;
- imaginea ligii la rezoluția ecranului.

Sigla a fost refăcută în mai mulți pași:

1. Prima serie de monograme, pe pătrate rotunjite, semăna cu iconița Adobe Photoshop.
2. Echipa a cerut un semn „îndrăzneț”, cu litere ascuțite, ca la LiveScore.
3. A respins și o a doua serie, apoi conceptele fără litere: literele trebuie să rămână baza siglei.
4. Dintre patru concepte cu litere a ales tăietura (L2). Dintre finisajele ei a ales varianta în două culori, care este sigla de acum.

## 1. Conceptul: PS tăiat

Sigla este formată din **literele P și S, înclinate și foarte groase, tăiate de o bară oblică** care urcă spre dreapta. Partea de deasupra tăieturii este albă, partea de dedesubt are culoarea de accent a ligii afișate. Sigla nu are pătrat, contur, minge sau scut: doar literele și tăietura.

- **Literele înclinate** dau senzația de viteză din grafica sportivă: LiveScore, tricourile și numerele de pe ele.
- **Tăietura** este gestul semnului: o diagonală ca o pasă sau ca linia unei tactici, care împarte sigla în două, cum se împarte un meci în două reprize.
- **Cele două culori** leagă sigla de liga afișată. Partea de jos e verde în Premier League, portocalie în La Liga, cyan în Serie A, roșie în Bundesliga și verde-lime în Ligue 1.

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

Lângă siglă, numele se scrie **PITCHSENSE** cu Kanit ExtraBold Italic, la 62% din înălțimea siglei: „PITCH” alb și „SENSE” în accentul ligii (`Lockup` din `app/ui/brand.py`). Într-o fereastră îngustă (sub 1180 px) rămâne doar sigla, iar numele apare la trecerea mausului.

### 2.3. Iconița aplicației

Iconița aplicației pune sigla pe un pătrat aproape negru, cu colțurile rotunjite (raza de 23% din latură, ca iconițele macOS). Pătratul e luminat din colțul de jos de culoarea adâncă a ligii (`paint_icon`, `icon_image`). Aplicația are imagini pentru mărimile 16, 24, 32, 48, 64, 128, 256, 512 și 1024 de pixeli (`app_icon`). Când utilizatorul schimbă liga, se schimbă și iconița ferestrei.

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

### 3.1. Suprafețe neutre, un accent pentru fiecare ligă

Suprafețele sunt aceleași pentru toate ligile: o noapte neutră, aproape neagră, cu carduri cu o treaptă mai deschise, ca în referințe (`app/ui/themes.py`, clasa `Theme`).

| Nume | Cod | Rol |
|---|---|---|
| Noapte | `#0A0A0C` | bara de sus și panoul ligilor |
| Fundal | `#0E0E11` | fereastra |
| Card | `#16161A` | cardurile și graficele |
| Card ridicat | `#1E1E23` | jetoanele, câmpurile, butoanele, scorul |
| Card de sus | `#28282E` | trecerea cu mausul și butoanele apăsate |
| Linie | `#2A2A30` | liniile dintre rânduri; marginea cardurilor e albă la 6% |
| Text | `#F5F5F7` | textul |
| Text secundar | `#9C9CA6` | explicații, capetele coloanelor |
| Text șters | `#5E5E68` | doar controalele dezactivate, niciodată text care trebuie citit |

**Culoarea ligii.** Culoarea ligii apare doar în câteva locuri, ca să nu coloreze tot ecranul:

- **accentul** (`accent`): ecranul ales, liga aleasă, butonul principal, rezultatul cel mai probabil, ora meciurilor care urmează, echipa ta;
- **textul de pe accent** (`accent_ink`);
- **accentul scris pe întuneric** (`accent_text`): mai deschis acolo unde accentul plin ar fi prea închis ca să se citească;
- **culoarea adâncă** (`brand`): în antet, în capul paginii unui meci sau al unei echipe și în iconiță.

| Ligă | Inspirație | Accent | Text pe accent | Accent ca text | Culoarea adâncă |
|---|---|---|---|---|---|
| Premier League | verdele și movul ligii | `#00FF85` | `#0A0A0C` | `#00FF85` | `#37003C` |
| La Liga | portocaliul și roșul ligii | `#FF7A3D` | `#0A0A0C` | `#FF8B55` | `#6E140E` |
| Serie A | cyanul și albastrul ligii | `#3DDCFF` | `#0A0A0C` | `#3DDCFF` | `#0B2A6F` |
| Bundesliga | roșul ligii | `#E2001A` | `#FFFFFF` | `#FF5A6A` | `#7A0410` |
| Ligue 1 | verdele-lime și bleumarinul ligii | `#D4FF3D` | `#0A0A0C` | `#D4FF3D` | `#0E1D45` |

La trecerea mausului, accentul se luminează cu 12%; în Bundesliga, unde textul de pe accent e alb, se întunecă (`#C70017`). Rândul echipei tale din tabele are accentul la 14% peste card.

**De ce așa.** În prima versiune, suprafețele colorate și luminile făceau ca tot ecranul să fie mov, roșu sau albastru. Accentele puternice, scrise subțire pe aceste fonduri, păreau toxice. În referințe, culoarea vie stă pe forme pline (pastile, butoane, un card), pe un fond neutru, și de aceea arată scump. Accentele ligilor au rămas cele alese de echipă; s-a schimbat felul în care sunt folosite.

**Ce nu se schimbă.** Unele culori rămân aceleași în toate ligile (`app/visualization/palette.py`):

- pătrățelele de formă (victorie `#157A47`, egal `#5F5F6A`, înfrângere `#C4314B`), bifa și crucea;
- culorile modelelor din grafice, validate pentru daltoniști.

Barele de probabilitate ale paginii unui meci sunt o singură familie de tonuri:

- victoria gazdelor în accentul ligii;
- egalul gri închis (`#3A3A42`);
- victoria oaspeților gri deschis (`#E6E6EB`).

Fiecare segment are procentul scris pe el, iar legenda numește segmentele.

### 3.2. Contrastul

Raporturile de contrast sunt calculate după WCAG 2.1 și verificate de `tests/test_themes.py` pentru fiecare paletă. Pragurile:

- textul are cel puțin 7 : 1;
- textul secundar, accentul folosit ca text și textul de pe accent au cel puțin 4,5 : 1.

Pe suprafețele neutre, textul are cel puțin 13,46 : 1, iar textul secundar cel puțin 5,39 : 1. Restul valorilor de mai jos sunt cele mai mici găsite. Ultimele două coloane sunt textul alb:

- pe capul paginii unui meci sau al unei echipe;
- pe fondul antetului, adică marginea imaginii ligii amestecată cu culoarea adâncă.

| Ligă | Accent ca text | Text pe accent | Text pe rândul echipei tale | Alb pe capul unui meci | Alb pe antet |
|---|---|---|---|---|---|
| Premier League | 12,36 | 14,73 | 12,01 | 17,30 | 16,33 |
| La Liga | 7,17 | 7,63 | 13,44 | 12,47 | 7,17 |
| Serie A | 10,18 | 12,13 | 12,33 | 13,82 | 10,95 |
| Bundesliga | 5,47 | 4,94 | 15,44 | 12,03 | 10,93 |
| Ligue 1 | 14,36 | 17,12 | 11,37 | 16,60 | 17,43 |

Testul verifică și procentele de pe barele de probabilitate, în fiecare ligă, și literele de pe pătrățelele de formă.

## 4. Literele

- **Plus Jakarta Sans** (Tokotype, licența SIL Open Font License 1.1) se folosește pentru toată interfața: navigarea, textul, tabelele, butoanele, jetoanele. Este scrisă normal, nu cu majuscule. Este o literă geometrică, ca literele aplicațiilor din referințe, și se citește bine la 11–14 px. Aplicația include grosimile 400, 500, 600, 700 și 800. A înlocuit Libre Franklin, o literă de ziar, în a doua versiune a Fazei 21.
- **Barlow Condensed** (Jeremy Tribby, SIL Open Font License 1.1) se folosește doar pentru ce se citește dintr-o privire: titlul mare al ecranului, scorurile, cifrele mari, numele echipelor pe pagina unui meci. Aplicația include grosimile 500, 600, 700 și 800.
- **Kanit** (Cadson Demak, SIL Open Font License 1.1) se folosește doar pentru siglă (Black Italic) și pentru numele de lângă ea (ExtraBold Italic). Am încercat și Unbounded și Chakra Petch; echipa a ales sigla desenată cu Kanit.

Toate trei au diacriticele românești corecte (ș și ț cu virgulă dedesubt). Fișierele și licențele (`OFL-PlusJakartaSans.txt`, `OFL-BarlowCondensed.txt`, `OFL-Kanit.txt`) sunt în `app/ui/assets/fonts/`. Qt le înregistrează la pornire (`load_fonts` din `app/ui/theme.py`), iar matplotlib la primul grafic. Dacă un font nu se încarcă, aplicația folosește un font al sistemului, iar autoverificarea raportează problema.

| Rol | Literă și mărime |
|---|---|
| titlul ecranului | Barlow Condensed, 56 px, 800, cu majuscule |
| cifrele mari | Barlow Condensed, 44 px, 700 |
| scorul pe pagina unui meci | Barlow Condensed, 64 px, 800 |
| numele echipelor pe pagina unui meci | Barlow Condensed, 24 px, 700, cu majuscule |
| navigarea | Plus Jakarta Sans, 14 px, 600 |
| titlurile cardurilor | Plus Jakarta Sans, 18 px, 700 |
| textul | Plus Jakarta Sans, 14 px |
| textul secundar | Plus Jakarta Sans, 13 px |
| etichetele mici | Plus Jakarta Sans, 11–12 px, 600–700 |

## 5. Interfața

### 5.1. Stilul

Interfața urmează referințele:

- **Fundalul** ferestrei este plat, noaptea neutră (`Backdrop`), fără lumini.
- **Cardurile** sunt plate: culoarea cardului, o margine albă la 6% și colțurile rotunjite cu raza de 20 px. În interior au 22–24 px de spațiu.
- **Pastilele** (raza de 18 px) sunt folosite pentru navigare, sub-file și filtre. Cea aleasă e plină cu accentul și are textul în noaptea ligii.
- **Butoanele** au raza de 12 px și fondul cardului ridicat. Butonul principal e plin cu accentul.
- **Antetul** fiecărui ecran este un card rotunjit (224 px înălțime, raza de 24 px), cu imaginea ligii (secțiunea 5.4).

### 5.2. Așezarea

- **Bara de sus** (68 px) are:
  - sigla cu numele;
  - cele patru ecrane (Meciuri, Clasament, Echipe, Analiză), scrise normal, cel ales ca pastilă plină cu accentul;
  - în dreapta, butonul „Actualizează datele” și butonul echipei tale, cu stema clubului și numele lui, ca profilul utilizatorului din referințe.
- **Panoul din stânga** are titlul „Competiții” și cele cinci ligi, fiecare cu steagul și țara ei. Liga aleasă e plină cu accentul ei, ca sportul ales din Sportia. Jos sunt versiunea, sursele și data actualizării.
- **Antetul** e descris în secțiunea 5.4.

| Ecran | Ce arată |
|---|---|
| Meciuri | Banda de zile: șapte jetoane („Azi / 15 oct.”), ziua aleasă plină cu accentul, săgeți rotunde. Sub ea: ziua, filtrele și modelul. Meciurile zilei sunt grupate pe ligă, fiecare ligă pe un card: steagul, numele ligii, „Spania · 3 meciuri” și legătura „Clasament ›”, apoi rândurile într-un chenar interior. Fiecare rând, ca în Sportia: ora (în accent) sau „Final”, gazdele cu stema în stânga, scorul („2 : 1”) sau „vs” pe o pastilă în mijloc, oaspeții cu stema în dreapta, apoi cele trei probabilități ale modelului ales. Cea mai mare probabilitate e plină cu accentul; la meciurile jucate are bifa sau crucea. În dreapta listei: cardul echipei tale, cu butonul principal „Pagina echipei”, și începutul clasamentului. |
| Pagina meciului | Capul meciului, luminat de sus de culoarea adâncă a ligii meciului: stemele mari, scorul sau „VS” și starea într-o pastilă de accent. Apoi barele celor trei modele, fiecare cu o frază simplă, cum vin echipele, scorurile probabile și harta lor. |
| Clasament | tabelul ligii cu stemele și ultimele cinci rezultate |
| Echipe | capul echipei, luminat de culoarea ligii, cu stema mare; șase cifre mari; forma; meciurile echipei; profilul K-Means; ratingul Elo și grupurile |
| Analiză | explicațiile algoritmilor, sezonul curent, măsurile de evaluare, cele cinci carduri de ligă (liga afișată are o margine în accent) și sursele |

**Colțurile din Meciuri.** Cardul unei ligi este desenat, nu stilizat (`LeagueGroup`):

- rândul de sub maus are propriul fundal rotunjit, în interiorul chenarului;
- liniile dintre rânduri nu ating marginile;
- ultimul rând nu mai are linie.

### 5.3. Schimbarea ligii

Când utilizatorul alege altă ligă, fereastra trece la culorile ei:

1. Aplicația păstrează o imagine a ferestrei de dinainte.
2. Trece fereastra la noua ligă: culorile, conținutul ecranelor, antetul.
3. Păstrează și o imagine a ferestrei noi.
4. Un cerc pornește din colțul din stânga sus și deschide imaginea veche spre cea nouă până trece de celelalte trei colțuri, în 0,8 s, cu o mișcare care încetinește spre final (`app/ui/transition.py`).

**Marginea cercului.** Marginea are valuri, ca în schimbarea culorilor din Material You („Monet”) de pe Android:

- sunt două valuri, de lungimi diferite, care se mișcă în sensuri opuse; între două creste ale celui principal sunt 120 px;
- sunt înalte de 18 px la pornire și se liniștesc la 4 px pe măsură ce cercul crește;
- în urma marginii vin două unde mai slabe, în accentul noii ligi.

**De ce sacada animația.** Au fost două cauze.

1. **Stratul transparent.** În prima versiune, animația era un strat transparent peste fereastră. Pentru fiecare cadru, Qt redesena tot ce era sub el. Acum stratul e opac și desenează doar cele două imagini ale ferestrei și linia valului, iar un cadru redesenează doar banda prin care a trecut marginea.
2. **Predicțiile calculate în fundal.** Ele împărțeau interpretorul Python cu fereastra, care aștepta după calcul la fiecare pas. Acum se calculează într-un proces separat.

Măsurat la rezoluția Retina, pe datele reale, cu o ligă în calcul în timpul animației:

| | Animația | Blocajul ferestrei înainte de animație |
|---|---|---|
| Înainte | 11 cadre, cu goluri de până la 270 ms | 4,8 s |
| Acum | 50 de cadre, la cel mult 17,6 ms unul de altul (60 pe secundă) | 0,5 s la prima deschidere a unei ligi |

Imaginea veche lasă clicurile să treacă, deci fereastra se poate folosi în timpul animației. O fereastră care nu este pe ecran (testele, autoverificarea) se schimbă fără animație.

Ca schimbarea să înceapă repede, aplicația restilizează doar fereastra, nu toată aplicația. Cu toate ecranele construite, schimbarea unei ligi deja încărcate, cu tot cu cele două imagini, durează aproximativ 0,3 s până pornește animația. Graficele de pe ecranele ascunse se redesenează abia când sunt deschise.

### 5.4. Imaginile ligilor

Imaginile DAZN sunt late și au jucătorii în dreapta. Antetul le arată astfel:

1. **Imaginea** ocupă dreapta antetului: cel mult 62% din lățime și cel mult 860 px, ca o fereastră foarte lată să nu taie capetele. Se desenează direct pe ecran, la rezoluția lui.
2. **Fondul** din stânga e culoarea marginii imaginii, amestecată pe jumătate cu culoarea adâncă a ligii. Marginea înseamnă media celor 3% din stânga ale fâșiei arătate, întunecată cu 30%.
3. **Trecerea.** Pe 50% din lățimea imaginii, de la marginea ei, fondul trece treptat în imagine. Pentru că fondul vine chiar din imagine, nu se vede nicio linie de îmbinare: imaginea pare luminată din dreapta.
4. **Umbra.** O umbră ușoară, dinspre stânga, dă adâncime sub titlu.

**De ce se pierdea calitatea în prima versiune.** Imaginea clară era pregătită într-o imagine intermediară de mărimea antetului în puncte. Pe un ecran Retina, unde un punct are doi pixeli, ea se desena apoi la jumătate din rezoluție. Peste o copie estompată, părea toată neclară. Acum nu mai există nicio imagine intermediară și nicio copie estompată.

### 5.5. O fereastră de orice lățime

Lățimea minimă a ferestrei este 1024 px. Niciun ecran nu are bară de derulare orizontală, la nicio lățime: verificarea s-a făcut la 1024, 1280 și 1440 px în teste și la 1024, 1180, 1280, 1440 și 1920 px pe datele reale.

| Când e mai îngust decât | Ce se schimbă |
|---|---|
| 1280 px (fereastra) | panoul ligilor păstrează doar steagurile (76 px); numele ligii apare la trecerea mausului |
| 1180 px (fereastra) | din siglă rămâne doar semnul, fără nume |
| 980 px (conținutul din Meciuri) | cardul echipei tale și clasamentul trec sub lista meciurilor, pe toată lățimea |
| 720 px (lista din Meciuri) | alegerea modelului trece sub filtre |
| 600 px (un rând de meci) | rândul pune gazdele și oaspeții pe două rânduri, cu scorul lângă ele, și probabilitățile dedesubt |
| 1000 px (conținutul din Echipe) | cardurile Forma, Meciurile echipei și Profilul K-Means trec unul sub altul |
| lățimea unei coloane | cele șase cifre ale echipei (cel puțin 128 px fiecare) și cele cinci carduri de ligă (cel puțin 210 px) trec pe rândul următor |

Piesele care fac asta sunt în `app/ui/widgets.py`:

- `ResponsiveBox` pune piesele alături sau una sub alta;
- `ReflowGrid` le așază pe atâtea coloane câte încap.

### 5.6. Echipa ta

Butonul echipei tale deschide o fereastră în care utilizatorul alege o ligă și o echipă din ultimul sezon. Alegerea este păstrată între porniri, împreună cu ultima ligă afișată, în `preferences.json`, în folderul utilizatorului (`app/services/preferences.py`). Un fișier lipsă sau deteriorat nu oprește aplicația.

Echipa aleasă:

- are cardul ei pe ecranul Meciuri (forma, următorul meci, ultimul rezultat, butonul „Pagina echipei”);
- are numele în accent în lista meciurilor, rândul nuanțat în clasamente și inelul în jurul stemei;
- este aleasă din start pe ecranul Echipe.

Dacă echipa joacă în altă ligă decât cea afișată, aplicația trece la liga ei.

### 5.7. Limba și scrierea numerelor

Interfața este în limba română; codul și comentariile rămân în engleză. Textul se scrie normal; doar titlul mare al ecranului și numele echipelor pe pagina unui meci sunt cu majuscule, în litera condensată. Tot textul afișat trece printr-un singur loc (`app/services/formatting.py` și `labels.py`):

- zecimale cu virgulă: 0,5776 și 53,4%;
- punct între mii: 7.600;
- semnul minus adevărat: −0,0073;
- datele ca zi.lună.an: 26.10.2025;
- sezoanele ca 2006/07;
- regula lui „de”: 1 meci, 19 meciuri, 20 de meciuri, 101 meciuri.

Mesajele tehnice ale erorilor rămân în engleză, dar sunt precedate de o explicație în română.

### 5.8. Componentele

Componentele folosesc stilul Qt Fusion și o paletă Qt și o foaie de stil generate din paleta ligii (`style_sheet` și `qt_palette` din `app/ui/theme.py`), deci arată la fel pe macOS și pe Windows. Elementele sunt stilizate după rol, nu unul câte unul. Piesele desenate citesc paleta ligii afișate de fiecare dată când se desenează (`current_theme`).

- **Tabelele** nu au linii de grilă: au doar o linie subțire sub fiecare rând și stau direct pe card. Numerele sunt aliniate la dreapta. Liniuța „–” marchează o valoare care nu există.
- **Pătrățelele de formă** au litera rezultatului (V, E, Î). Culoarea doar o repetă, deci rezultatul se citește și de daltoniști.
- **Bifa și crucea** de pe meciurile jucate urmează aceeași regulă: forma spune dacă predicția s-a nimerit, culoarea doar o repetă.
- **Jetoanele zilelor fără meciuri** nu au fundal și au textul secundar: se pot alege și trebuie să se poată citi.

## 6. Graficele

Graficele au fundal transparent: stau pe card, în culorile oricărei ligi (`ChartView` și `on_surface` din `charts.py`). Au text deschis, textul cu Plus Jakarta Sans, titlurile cu Barlow Condensed și grile subțiri. Fiecare culoare are un singur rol:

| Rol | Culori | Regulă |
|---|---|---|
| Identitatea modelelor | Elo `#4D8DFF`, Poisson `#EF5A6F`, regresie logistică `#00A3A8`; referința `#8E929C`, punctată | fiecare model are mereu aceeași culoare, pe toate graficele și în toate ligile |
| Grupurile K-Means (ordonate după putere) | `#D2E2FF`, `#8EB4FF`, `#5585F0`, `#3A63C9` | un singur albastru, de la luminos (elita) la adânc (slabă peste tot) |
| Mărimi (probabilități, număr de meciuri) | albastru în șase repere, de la `#1C2A52` la `#DCE8FF` | mai luminos înseamnă mai mult |
| Avantajul gazdelor | celelalte sezoane `#4D8DFF`, 2020/21 `#EF5A6F` | o pereche validată |
| Evidențierea | accentul ligii | un singur lucru: sezonul ales (Elo), echipa aleasă (grupuri) |

Graficele se construiesc cu un auriu pentru evidențiere și cu culoarea cardului din `palette.py` pentru inelele marcajelor. La afișare, `on_surface` înlocuiește aceste două culori cu accentul și cu cardul ligii afișate. La fiecare schimbare a ligii, le înlocuiește din nou.

**Validarea culorilor modelelor** (rularea din 2026-10-05, în modul întunecat): cele trei culori ale modelelor trec verificările pentru linii care se pot întâlni. Cea mai mică distanță pentru daltonism este 11,3, la perechea Poisson–regresie logistică (pragul este 8).

**Desen.** Liniile au 2 px, iar marcajele au un inel de culoarea cardului. Celulele hărților de căldură sunt despărțite de spații de 2 px. Gradațiile axelor sunt la distanțe de 1, 2 sau 5 unități, cu virgulă zecimală.

## 7. Fișierele

| Fișier | Conține |
|---|---|
| `app/ui/themes.py` | suprafețele comune și accentele celor cinci ligi |
| `app/visualization/palette.py` | culorile care nu se schimbă (formă, modele, grupuri, grafice) |
| `app/ui/brand.py` | sigla tăiată, iconița, sigla cu numele, steagurile, ecusoanele, stemele, imaginile ligilor |
| `app/ui/theme.py` | fonturile, paleta Qt și foaia de stil, generate din paleta unei ligi |
| `app/ui/transition.py` | schimbarea culorilor: cercul cu valuri peste cele două imagini ale ferestrei |
| `app/ui/widgets.py` | piesele desenate ale interfeței, antetul cu imaginea ligii, `ResponsiveBox`, `ReflowGrid` |
| `app/ui/match_widgets.py` | banda de zile, rândul de meci, capetele coloanelor de probabilități, bifa și crucea |
| `app/ui/assets/fonts/` | Plus Jakarta Sans (cinci grosimi), Barlow Condensed (patru), Kanit (două) și licențele |
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
  - că suprafețele sunt aceleași în toate ligile și că fiecare ligă are accentul ei;
  - contrastele din secțiunea 3.2, inclusiv antetul cu imaginea reală a fiecărei ligi;
  - procentele de pe barele de probabilitate și literele de pe pătrățelele de formă;
  - că foaia de stil a fiecărei ligi folosește doar accentul ei.
- `tests/test_transition.py` verifică:
  - cercul crește până trece de colțul cel mai îndepărtat;
  - valurile se liniștesc, urcă și coboară de-a lungul marginii și se mișcă în timp;
  - marginea merge de la marginea de sus la cea din stânga;
  - partea cu imaginea veche se micșorează de la toată fereastra la nimic;
  - la jumătate, imaginea nouă e în cerc și cea veche în afara lui;
  - stratul e opac (nimic de sub el nu se redesenează), lasă clicurile să treacă și dispare la final.
- `tests/test_ui.py` verifică:
  - schimbarea culorilor ferestrei la alegerea ligii, cu sau fără animație, și o schimbare întreruptă de alta;
  - fereastra îngustă (doar steagurile, doar semnul);
  - că niciun ecran nu se derulează în lateral la 1024, 1280 și 1440 px;
  - `ResponsiveBox`, `ReflowGrid`, rândul de meci îngust și ultimul rând al unei ligi;
  - antetul: imaginea neatinsă în dreapta, fondul din culoarea marginii ei, explicația la stânga imaginii;
  - graficul ascuns, redesenat la deschidere.
- `tests/test_charts.py` verifică trecerea unui grafic pe cardul altei ligi.
- `tests/test_icons.py` verifică faptul că iconița pachetelor este sigla în culorile La Ligii.
- Autoverificarea (`python -m app --self-test`, 25 de verificări) verifică și culorile ligii, și valul.
- Pe 2026-10-15, ecranele au fost desenate cu datele reale, la rezoluția Retina (`QT_SCALE_FACTOR=2`), și verificate vizual:
  - în toate cele cinci ligi;
  - la 1100 și 1440 px;
  - animația în patru momente ale ei, cu timpul fiecărui cadru măsurat.

## 9. Limitări

- Interfața are doar tema întunecată, și când sistemul folosește modul luminos.
- Pachetele au iconița în culorile La Ligii, pentru că sistemul o citește din pachet înainte ca aplicația să pornească. Fereastra ia apoi culorile ligii afișate.
- Mesajele de la pornire, afișate înainte să existe fereastra, și indiciile de la trecerea mausului au culorile La Ligii.
- Animația a fost măsurată pe o fereastră desenată fără ecran, la rezoluția Retina. Fluiditatea pe ecranul real depinde și de placa video și de sistem.
- Stemele sunt mărci ale cluburilor. Sunt incluse doar în depozitul privat și în pachete, pentru recunoașterea echipelor, și nu trebuie publicate. Imaginile ligilor (DAZN) aparțin deținătorilor lor și, ca stemele, nu se publică.
