# Identitatea vizuală PitchSense

Acest document descrie sigla, culorile, literele și regulile interfeței PitchSense (Faza 16) și explică de ce a fost ales fiecare element. Publicul aplicației sunt colegii și profesorii care urmăresc fotbalul. Aplicația trebuie să arate ca site-urile de fotbal pe care le folosesc deja: site-ul FC Barcelona, LiveScore, OneFootball. Asta înseamnă:

- o temă întunecată;
- titluri condensate, scrise cu majuscule;
- carduri de meci;
- un singur accent de culoare care arată unde să te uiți.

Faza a avut trei încercări de siglă:

1. un semn neutru, pe o temă deschisă la culoare;
2. o stemă de club pe o temă întunecată, pe care echipa a găsit-o prea apropiată de stema Barcelonei;
3. monograma PS, întâi cu o minge veche de piele, aurie, în bucla lui P.

Echipa a ales apoi dintre trei variante ale monogramei: fără minge, cu silueta mingii în fundal (doar contur alb, transparent) și cu liniile terenului în fundal. A ales-o pe prima, cea minimalistă, care este sigla de acum. Tema întunecată și culorile blaugrana au rămas.

## 1. Conceptul: monograma PS

Sigla este o **monogramă pe un pătrat cu colțurile rotunjite**, cum au aplicațiile de scoruri: LiveScore își pune inițialele „LS” pe un pătrat portocaliu. Inițialele PitchSense, **P** și **S**, sunt albe, groase și geometrice, așezate una lângă alta, și nu mai e nimic altceva pe pătrat. O siglă atât de simplă se recunoaște dintr-o privire și rămâne clară și la 16 pixeli.

- **Litera P** are bucla un cerc întreg, cu un gol rotund care atinge piciorul.
- **Litera S** este făcută din două jumătăți de inel, una deasupra celeilalte. Are aceeași grosime și aceeași înălțime ca P.
- **Pătratul** trece în diagonală de la albastru (stânga sus) la grena (dreapta jos): culorile blaugrana, ca un omagiu adus Barcelonei, echipa preferată a autorului. Din stema Barcelonei nu apare nimic: nici scutul, nici crucea, steagul Cataloniei, literele „FCB”, dungile sau mingea.

## 2. Formele

### 2.1. Geometria siglei

Sigla se desenează pe un pătrat de 100 × 100 de unități, cu QPainter (`paint_logo` din `app/ui/brand.py`, singura sursă a desenului). Literele sunt construite din cercuri și dreptunghiuri unite sau scăzute (`letter_p`, `letter_s`), nu scrise cu un font, ca să fie exact la fel pe orice sistem.

| Element | Desen |
|---|---|
| Pătratul | 100 × 100, colțurile rotunjite cu raza 23 (ca iconițele macOS), gradient de la albastru `#0B5BB8` la grena `#B3004E` |
| Literele | albe (`#F2F4F8`), grosimea 11, înălțimea 62, de la y = 19 până la y = 81; între P și S sunt 3 unități; perechea este centrată |
| Litera P | piciorul și o buclă rotundă cu raza exterioară 22,5, legată de picior prin două linii drepte, sus și jos; golul buclei are raza 11,5 și atinge piciorul |
| Litera S | două jumătăți de inel cu raza 18,25: cea de sus deschisă în dreapta jos, cea de jos în stânga sus; linia din mijloc este comună |

**Mărimi mici.** Sigla rămâne aceeași la toate mărimile, de la 1024 la 16 pixeli: nu are detalii care să se piardă.

**Spațiul liber.** În jurul siglei se lasă liber cel puțin o grosime de literă. Sigla nu se rotește, nu se deformează și nu primește umbră.

### 2.2. Sigla cu numele

Lângă siglă, numele se scrie **PITCHSENSE** cu Barlow Condensed ExtraBold: „PITCH” alb și „SENSE” auriu (`Lockup` din `app/ui/brand.py`). Sub bara de sus se întinde o linie subțire, albastră pe jumătatea stângă și grena pe cea dreaptă.

### 2.3. Iconița aplicației

Iconița aplicației este chiar sigla, care umple pătratul (`icon_image`). Aplicația are imagini pentru mărimile 16, 24, 32, 48, 64, 128, 256, 512 și 1024 de pixeli (`app_icon`). Pentru pachete, `packaging/icons.py` salvează aceleași imagini în `PitchSense.icns` (macOS, unsprezece imagini de la 16 la 1024 de pixeli) și `PitchSense.ico` (Windows, șapte imagini de la 16 la 256 de pixeli), la fiecare construire (Faza 17).

### 2.4. Steagurile și ecusoanele

- **Ligile** au steagul rotund al țării lor, ca în listele LiveScore și OneFootball: Anglia, Spania, Italia, Germania și Franța (`flag_pixmap`). Steagurile țărilor nu aparțin nimănui. Siglele ligilor sunt mărci înregistrate și nu sunt folosite.
- **Echipele** au un ecuson rotund cu trei litere, ca pe tabela de marcaj a unei transmisiuni TV: BAR, RMA, MUN, NFO (`team_badge`; prescurtarea vine din `team_abbreviation`, în `app/services/labels.py`). Stemele cluburilor nu sunt folosite: sunt mărci înregistrate și nu fac parte din date. Echipa ta are ecusonul cu inel și litere aurii.

## 3. Culorile

| Nume | Cod | Rol |
|---|---|---|
| Noapte adâncă | `#070B17` | bara de sus și panoul ligilor |
| Noapte | `#0B1020` | fundalul ferestrei |
| Card | `#141B30` | cardurile și graficele |
| Card ridicat | `#1C2541` | capetele tabelelor, câmpurile de alegere, trecerea cu mausul |
| Card de sus | `#253052` | butoanele apăsate, rândurile alese |
| Linie | `#2A3557` | margini și separatoare |
| Text | `#F2F4F8` | textul (alb-cretă, nu alb pur) |
| Text secundar | `#A3ADC6` | explicații, capetele coloanelor |
| Blau | `#0B5BB8` | pătratul siglei (sus, stânga), linia de sub bara de sus, lumina eroului |
| Grena | `#B3004E` | pătratul siglei (jos, dreapta), linia de sub bara de sus, lumina eroului |
| Aur | `#EDBB00` | singurul accent: ecranul ales, liga aleasă, butonul principal, echipa ta, sezonul și echipa evidențiate pe grafice |
| Nuanță aurie | `#2E2E2A` | fundalul rândului echipei tale în tabele |

Valorile sunt definite o singură dată, în `app/visualization/palette.py`, și folosite atât de interfață, cât și de grafice.

**De ce întunecat.** Site-urile de fotbal moderne sunt întunecate, iar tema întunecată pune în valoare culorile echipelor și cifrele mari. Am urmat regulile obișnuite ale unei teme întunecate:

- bleumarin foarte închis în loc de negru pur;
- alb-cretă în loc de alb pur, ca textul să nu „ardă”;
- adâncimea se arată prin suprafețe tot mai deschise (fereastră, card, card ridicat), nu prin umbre;
- culorile de accent sunt ușor stinse, ca să rămână lizibile.

**De ce blaugrana adaptat.** Albastrul (`#004D98`) și grena (`#A50044`) oficiale ale Barcelonei se pierd pe un fundal aproape negru. De aceea, sigla și liniile folosesc variante mai luminoase, din aceeași familie.

**De ce aurul.** Galbenul-auriu este a treia culoare a site-ului Barcelonei (butonul de bilete, mingea galbenă din stemă) și culoarea trofeelor. Pe fiecare ecran marchează un singur lucru: unde să te uiți.

### 3.1. Contrastul

Raporturi de contrast după WCAG 2.1, calculate din codurile culorilor și verificate de `tests/test_brand.py` (pragul pentru text este 4,5 : 1):

| Text pe fundal | Contrast |
|---|---|
| text pe noapte / card / card ridicat | 17,19 / 15,52 / 13,72 : 1 |
| text secundar pe noapte / card / card ridicat | 8,43 / 7,61 / 6,73 : 1 |
| text pe nuanța aurie (echipa ta) | 12,38 : 1 |
| aur pe noapte / card | 10,56 / 9,53 : 1 |
| noapte adâncă pe aur (butonul principal) | 10,95 : 1 |
| alb pe gazde / oaspeți și noapte adâncă pe egal (barele de probabilitate) | 5,40 / 5,87 / 6,14 : 1 |
| alb pe victorie / egal / înfrângere (forma) | 5,38 / 5,63 / 5,40 : 1 |

## 4. Literele

- **Barlow Condensed** (Jeremy Tribby, licența SIL Open Font License 1.1) se folosește pentru titluri, cifre mari, scor, navigare și sub-file, aproape mereu cu majuscule. Este o literă condensată, ca titlurile de pe site-ul Barcelonei și din presa sportivă: încape mult text pe puțin loc și se citește dintr-o privire. Aplicația include grosimile 500, 600, 700 și 800.
- **Libre Franklin** (Impallari Type, licența SIL Open Font License 1.1) se folosește pentru textul obișnuit, tabele și explicații. Aplicația include grosimile 400, 500, 600, 700 și 800. Este o reinterpretare a clasicului Franklin Gothic, litera ziarelor și a paginilor de sport; se potrivește cu o literă condensată, cum Franklin Gothic se potrivea cu variantele lui condensate.

Ambele fonturi au toate diacriticele românești corecte (ș și ț cu virgulă dedesubt). Fișierele și licențele (`OFL-BarlowCondensed.txt`, `OFL-LibreFranklin.txt`) sunt în `app/ui/assets/fonts/`. Qt le înregistrează la pornire (`load_fonts` din `app/ui/theme.py`), iar matplotlib la primul grafic. Dacă un font nu se încarcă, aplicația folosește un font al sistemului, iar autoverificarea raportează problema.

Fiecare rol de text are o mărime fixă:

| Rol | Literă și mărime |
|---|---|
| titlul ecranului | 46 px, 800 |
| cifrele mari | 46 px, 700 |
| scorul | 58 px, 800 |
| numele echipelor din cardul de meci | 26 px, 700 |
| navigarea | 18 px, 600 |
| titlurile secțiunilor | 21 px, 700 |
| textul | 14 px |
| textul secundar | 13 px |
| etichetele scrise cu majuscule | 12 px, 700 |

## 5. Interfața

### 5.1. Așezarea

Așezarea urmează LiveScore și site-ul Barcelonei:

- **Bara de sus** are sigla cu numele, cele cinci ecrane cu majuscule (cel ales are dedesubt o linie aurie) și, în dreapta, butonul auriu „Echipa ta”. Sub bară se întinde linia albastru–grena.
- **Panoul din stânga** are titlul „COMPETIȚII” și cele cinci ligi, fiecare cu steagul și țara ei. Liga aleasă are fundalul ridicat și o linie aurie în stânga. Jos sunt sursa datelor și grupa.
- **Eroul** este capul fiecărui ecran: un gradient de noapte luminat discret în albastru și grena, cu liniile terenului (linia de mijloc, cercul central, careul) abia vizibile. Peste el apar liga (cu steag, auriu, cu majuscule), titlul ecranului cu litere mari și o explicație.
- **Conținutul** stă în carduri cu colțurile rotunjite (14 px), pe fundalul noapte.

| Ecran | Ce arată |
|---|---|
| Acasă | patru cifre mari (meciuri, sezoane, echipe, meciuri evaluate), modelul cu cel mai mic scor Brier (și dacă avantajul lui este real), echipa ta (ecuson, loc, puncte, ultimele cinci rezultate, rating Elo) și rezultatele modelelor |
| Predicție | **cardul meciului**: ecusoanele și numele echipelor, scorul cu cifre mari sau „VS” și, pentru fiecare model, o bară împărțită în victorie gazde (albastru), egal (gri) și victorie oaspeți (grena), cu procentele în ea și cel mai probabil rezultat îngroșat; dedesubt, cifrele exacte, golurile așteptate, scorurile probabile și harta scorurilor (Poisson) |
| Echipe | clasamentul la orice dată, cu ecusoanele echipelor, profilul unei echipe (cu ultimele cinci rezultate în pătrățele colorate, ca într-un ghid de formă), ratingul Elo și grupurile K-Means |
| Modele | măsurile de evaluare, diferențele reale dintre modele, împărțirea pe subseturi, calibrarea și matricea de confuzie |
| Ligi | cinci **carduri de ligă** (steag, procentul victoriilor gazdelor cu cifre mari, golurile pe meci, modelul cu cel mai mic scor Brier); un clic deschide liga. Dedesubt sunt comparațiile, în tabele și grafice. |

### 5.2. Echipa ta

Butonul „Echipa ta” deschide o fereastră în care utilizatorul alege o ligă și o echipă din ultimul sezon. Alegerea este păstrată între porniri, împreună cu ultima ligă afișată, în `preferences.json`, în folderul utilizatorului (`app/services/preferences.py`). Un fișier lipsă sau deteriorat nu oprește aplicația. O alegere care nu poate fi salvată rămâne valabilă până la închidere.

Echipa aleasă:

- apare pe ecranul Acasă;
- are în clasamente rândul auriu și ecusonul cu inel auriu;
- este aleasă din start în ecranele Predicție (ultimul ei meci al sezonului) și Echipe.

Dacă echipa joacă în altă ligă decât cea afișată, aplicația trece la liga ei.

### 5.3. Limba și scrierea numerelor

Interfața este în limba română; codul și comentariile rămân în engleză. Tot textul afișat trece printr-un singur loc (`app/services/formatting.py` și `labels.py`):

- zecimale cu virgulă: 0,5776 și 53,4%;
- punct între mii: 7.600;
- semnul minus adevărat: −0,0073;
- datele ca zi.lună.an: 26.10.2025;
- sezoanele ca 2006/07;
- regula lui „de”: 1 meci, 19 meciuri, 20 de meciuri, 101 meciuri.

Numele modelelor, ale rezultatelor, ale țărilor și prescurtările echipelor sunt traduse sau calculate doar la afișare. Jurnalele de predicții și codul își păstrează identificatorii în engleză. Mesajele tehnice ale erorilor rămân în engleză, dar sunt precedate de o explicație în română.

### 5.4. Componentele

Toate componentele folosesc stilul Qt Fusion, o paletă Qt întunecată și o singură foaie de stil (`STYLE_SHEET` din `app/ui/theme.py`), deci arată la fel pe macOS și pe Windows. Elementele sunt stilizate după rol, nu unul câte unul. Piesele desenate (eroul, linia albastru–grena, cifrele mari, barele de probabilitate, pătrățelele de formă, butoanele ligilor) sunt în `app/ui/widgets.py`.

- **Butoanele** au colțurile rotunjite. Butonul principal (o singură acțiune importantă pe ecran) este auriu, cu text închis.
- **Tabelele** nu au linii de grilă, au rânduri de 36 px și capete pe fundal ridicat. Numerele și titlurile coloanelor de numere sunt aliniate la dreapta. Liniuța „–” marchează o valoare care nu există.
- **Sub-filele** au numele cu majuscule și, dedesubt, o linie aurie. Înălțimea lor urmează pagina afișată.
- **Listele și casetele de bifat** au săgeata și bifa desenate de noi (`app/ui/assets/icons/`). Bifa și butonul radio ales sunt aurii.
- **Pătrățelele de formă** au litera rezultatului (V, E, Î). Culoarea (verde, gri, roșu) doar o repetă, deci rezultatul se citește și de daltoniști, care nu deosebesc verdele de roșu.

## 6. Graficele

Graficele au fundalul cardurilor, text deschis, titluri cu Barlow Condensed și grile subțiri (`app/visualization/charts.py`). Fiecare culoare are un singur rol:

| Rol | Culori | Regulă |
|---|---|---|
| Identitatea modelelor | Elo `#4D8DFF`, Poisson `#EF5A6F`, regresie logistică `#00A3A8`; referința `#8E929C`, punctată | fiecare model are mereu aceeași culoare, pe toate graficele; referința este gri și punctată, ca modelele să rămână în față |
| Grupurile K-Means (ordonate după putere) | `#D2E2FF`, `#8EB4FF`, `#5585F0`, `#3A63C9` | un singur albastru, de la luminos (elita) la adânc (slabă peste tot), pentru că grupurile au o ordine |
| Mărimi (probabilități, număr de meciuri) | albastru în șase repere, de la `#1C2A52` la `#DCE8FF` | mai luminos înseamnă mai mult; cifrele din celule sunt închise pe celulele luminoase și deschise pe cele întunecate |
| Avantajul gazdelor | celelalte sezoane `#4D8DFF`, 2020/21 `#EF5A6F` | o pereche validată |
| Evidențierea | aur | un singur lucru: sezonul ales (Elo), echipa aleasă (grupuri) |

**Validare** (rulare din 2026-10-05, cu validatorul de palete al ghidului de vizualizare, în modul întunecat, pe culoarea cardului):

- Cele trei culori ale modelelor trec toate verificările pentru grafice în care oricare două linii se pot întâlni. Cea mai mică distanță pentru daltonism este 11,3, la perechea Poisson–regresie logistică (pragul este 8).
- Perechea albastru–roșu a graficului avantajului gazdelor trece: distanța este 21,2.
- Barele cardului de meci (gazde `#2B63D9`, egal `#8790A6`, oaspeți `#C2185B`) sunt doi poli, albastru și grena, în jurul unui gri neutru; distanța cea mai mică pentru daltonism este 12,9. Un prim gri, mai închis (`#4A5470`), stătea la doar 3,5 de grena, așa că a fost luminat, iar procentele de pe el sunt scrise închis.
- Rampa grupurilor trece ca rampă ordonată (capătul ei cel mai întunecat are 3,10 : 1 față de card).
- Aurul este prea luminos pentru o serie de date, așa că este folosit doar pentru evidențiere.
- Prima încercare (`#4D8DFF`, `#F0527F`, `#2BC79A`) a picat: verdele-turcoaz era prea luminos pentru un fundal întunecat, iar perechea zmeuriu–verde era prea apropiată pentru daltonism (6,7). Setul de acum a fost găsit încercând, cu validatorul, mai multe variante de roșu și de turcoaz.

**Desen.** Liniile au 2 px, iar marcajele au un inel de culoarea cardului. Celulele hărților de căldură sunt despărțite de spații de 2 px. Titlurile sunt aliniate la stânga, iar legendele cu nume lungi stau sub grafic. Gradațiile axelor sunt la distanțe de 1, 2 sau 5 unități și au exact câte zecimale le trebuie, cu virgulă: 0,8 – 1,0 – 1,2, nu 1,25 rotunjit la „1,2”.

## 7. Fișierele

| Fișier | Conține |
|---|---|
| `app/visualization/palette.py` | toate culorile |
| `app/ui/brand.py` | sigla (literele și pătratul), iconița, sigla cu numele, steagurile, ecusoanele, liniile terenului din erou |
| `app/ui/theme.py` | fonturile, paleta Qt și foaia de stil |
| `app/ui/widgets.py` | piesele desenate ale interfeței |
| `app/ui/assets/fonts/` | Barlow Condensed (patru grosimi), Libre Franklin (cinci grosimi) și licențele |
| `app/ui/assets/icons/` | săgeata listelor și bifa |

## 8. Verificare

- `tests/test_brand.py` verifică:
  - geometria siglei: literele una lângă alta, centrate și de aceeași înălțime, golul rotund al lui P lipit de picior;
  - culorile siglei, citite din imaginea desenată: literele albe, golul lui P care arată pătratul, pătratul albastru sus și grena jos, colțurile transparente, nicio urmă de auriu;
  - iconița și toate mărimile ei;
  - steagurile, cu culorile fiecărei țări, și inelul auriu al echipei tale;
  - fonturile și diacriticele lor;
  - toate contrastele din secțiunea 3.1.
- `tests/test_ui.py` verifică navigarea, alegerea ligii din panou și din cardurile ligilor, „echipa ta”, cardul meciului, barele de probabilitate, pătrățelele de formă și evidențierea rândurilor.
- `tests/test_charts.py` verifică tema întunecată a graficelor, referința punctată și lizibilitatea cifrelor din celule.
- Autoverificarea (`python -m app --self-test`) verifică încărcarea ambelor fonturi și a iconițelor SVG, pentru că un pachet trebuie să le conțină.
- Toate ecranele au fost desenate cu datele reale și verificate vizual (2026-10-05).

## 9. Limitări

- Interfața are doar tema întunecată, și când sistemul folosește modul luminos.
- Echipele au ecusoane cu inițiale, nu stemele lor: stemele sunt mărci înregistrate și nu fac parte din date.
