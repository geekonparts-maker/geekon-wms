# Handoff: GeekOn WMS — Mobile Interface για Mantis LVS (Android PDA)

## Overview
Touch-first mobile interface για χειριστές αποθήκης (RF operators) πάνω στο Mantis Logistics Vision Suite (LVS) WMS. Τρέχει σε Android PDA με ενσωματωμένο scanner (Honeywell EDA52-class, οθόνη 5.5", 360×720 CSS px). Καλύπτει: login, dashboard εργασιών, παραλαβή, τοποθέτηση, picking, packing, αναπλήρωση, απογραφή, μετακινήσεις, αναζήτηση stock και εκτύπωση ετικετών barcode.

## About the Design Files
Τα αρχεία του πακέτου είναι **design references φτιαγμένα σε HTML** (prototypes που δείχνουν την επιδιωκόμενη εμφάνιση και συμπεριφορά) — ΔΕΝ είναι production κώδικας για απευθείας αντιγραφή. Στόχος είναι να **αναδημιουργηθούν στο περιβάλλον της ομάδας** (π.χ. React/Ionic/Capacitor, Flutter, ή native Android/Kotlin) με τα δικά της patterns και βιβλιοθήκες. Αν δεν υπάρχει υφιστάμενο περιβάλλον, προτεινόμενη στοίβα: **React + Vite PWA** (βλ. Deployment) ώστε το PDA να φορτώνει πάντα την τελευταία έκδοση από URL.

- `GeekOn WMS.dc.html` — το πλήρες λειτουργικό prototype (κύρια αναφορά). Ανοίγει απευθείας σε browser (χρειάζεται το `support.js` δίπλα του).
- `WMS PDA Interface (options).dc.html` — οι 3 αρχικές σχεδιαστικές κατευθύνσεις (ιστορικό/εναλλακτικές).
- `assets/` — το logo GeekOn σε 3 εκδοχές (για ανοιχτό, σκούρο, πορτοκαλί φόντο), transparent PNG.

## Fidelity
**High-fidelity (hifi).** Χρώματα, τυπογραφία, αποστάσεις, radius και interactions είναι τελικά. Αναπαραγωγή pixel-perfect με τις βιβλιοθήκες του codebase.

## Πλήρης λίστα λειτουργιών (features)
1. **Login** — PIN 4 ψηφίων σε numpad ή σάρωση badge. (Demo: οποιοδήποτε 4ψήφιο PIN.)
2. **Dashboard** — χαιρετισμός χρήστη, βάρδια/ζώνη, ένδειξη Online, σύνολο εκκρεμών εργασιών, κουμπί «Ξεκίνα», grid 9 modules με live counters (✓ όταν ολοκληρωθεί).
3. **Παραλαβή (RCV)** — γραμμές ASN με progress bar ανά SKU· κάθε scan σωστού SKU +1· «Κλείσιμο παραλαβής» όταν συμπληρωθούν όλα.
4. **Τοποθέτηση (PUT)** — ΧΩΡΙΣ παλέτα: scan προϊόντος → προτεινόμενη θέση συστήματος → scan της πρότασης Ή **οποιασδήποτε άλλης έγκυρης θέσης** (καταχωρείται ως αλλαγή πρότασης με σχετικό μήνυμα).
5. **Picking (directed)** — εμφανίζεται μεγάλη η θέση + κάρτα είδους (SKU, παρτίδα, όνομα, x/y)· σαρώνεται **μόνο το προϊόν**· στο x/x **auto-advance** στο επόμενο είδος χωρίς κουμπί επιβεβαίωσης· progress bar παραγγελίας· preview επόμενης γραμμής· οθόνη ολοκλήρωσης με στατιστικά.
6. **Αναπλήρωση θέσης μέσα από το Picking** — κουμπί «Αναπλήρωση θέσης X»: scan θέσης προέλευσης → scan της θέσης picking → επιστροφή στο picking στο ίδιο σημείο.
7. **Packing** — scan ειδών μέσα στο κιβώτιο, «Κλείσιμο κιβωτίου & ετικέτα».
8. **Αναπλήρωση (RPL)** — free-form: scan προϊόντος (κάθε scan +1) με − / + για χειροκίνητη ποσότητα → «Συνέχεια» → scan θέσης προέλευσης → scan θέσης προορισμού.
9. **Μετακίνηση (MOV)** — ίδια ροή με την αναπλήρωση (προϊόν+ποσότητα → από → προς).
10. **Απογραφή (INV)** — τυφλή κυκλική καταμέτρηση: scan θέσης → **κάθε scan τεμαχίου +1** (ή numpad) → OK· σε διαφορά: οθόνη «Διαφορά απογραφής» με «Ξαναμέτρα» / «Αποδοχή διαφοράς».
11. **Αναζήτηση (FND)** — SKU ή θέση, με scan ή πληκτρολόγηση· αποτέλεσμα: όνομα + θέσεις/ποσότητες· κουμπί «Εκτύπωση ετικέτας barcode».
12. **Ετικέτες (LBL)** — παραγωγή **πραγματικού Code 128** barcode για SKU ή θέση (αλγόριθμος στο prototype: πίνακας 107 patterns, Start B, checksum mod 103, stop), quick chips, αντίτυπα − / +, «Εκτύπωση» (στην υλοποίηση: αποστολή ZPL σε Zebra/Honeywell printer).
13. **Scan feedback** — σε κάθε scan: ήχος (WebAudio: επιτυχία 1046→1568 Hz sine, σφάλμα 196 Hz sawtooth 220ms), δόνηση (`navigator.vibrate`: [40] ok / [80,40,80] error), πράσινο/κόκκινο flash overlay 350/450ms, toast μηνύματα.
14. **Keyboard-wedge scanning** — global keydown buffer, Enter = ολοκλήρωση scan· αγνοείται όταν το focus είναι σε input. Έτσι δουλεύει out-of-the-box με Honeywell/Zebra scanner σε wedge mode.
15. **Προφίλ** — στατιστικά χρήστη (picks, ακρίβεια, γραμμές/ώρα), αποσύνδεση.
16. **Bottom nav** — Αρχική / Εργασίες / Αναζήτηση / Προφίλ (εμφανίζεται μόνο εκτός ροών).
17. **Scanner Simulator** (demo-only panel εκτός συσκευής) — να ΜΗΝ υλοποιηθεί στο production.

## Screens / Views
Κάθε οθόνη στο prototype έχει `data-screen-label`. Κοινή δομή ροών: πορτοκαλί header (radius 0 0 26px 26px) με back ‹ (36px κύκλος, rgba(255,255,255,.18)), τίτλο/υπότιτλο κέντρο, chip προόδου mono δεξιά· σώμα με κάρτες· dashed πορτοκαλί «scan hint» box.

- **Login**: μαύρο (#17191E) πάνω μέρος με logo (on-dark, ύψος 52px) + tagline letterspaced· λευκό sheet (radius 26px πάνω) με κουμπί «Σάρωση badge» (56px, #17191E), divider «ή με PIN», 4 dots (13px, γεμίζουν #ED872D), numpad 3×4 (κουμπιά 52px, radius 26px, bg #F4F5F7).
- **Dashboard**: orange header + floating λευκή κάρτα (−26px overlap, radius 18px, shadow 0 6px 18px rgba(23,25,30,.08)) + grid 2 στηλών tiles (radius 18px, chip 34px #FDF1E6 με mono κωδικό #ED872D, counter 18px/800).
- **Picking**: κάρτα θέσης (loc 36px IBM Plex Mono 700, zone chip), κάρτα είδους (qty x/y 24px mono #ED872D), hint, ghost κουμπί αναπλήρωσης (46px, border #E2E5EA), strip «ΕΠΟΜΕΝΟ».
- **Αναπλήρωση/Μετακίνηση**: κάρτα ΑΠΟ → ΠΡΟΣ (ενεργή φάση #ED872D, ολοκληρωμένη #22A55C, ανενεργή #9AA0AB), stepper − / + (44px κύκλοι).
- **Απογραφή**: μεγάλος μετρητής 40px mono, numpad, κόκκινη κάρτα διαφοράς (#FDECEC, border #E05252).
- **Ετικέτες**: λευκή κάρτα-ετικέτα με όνομα, μπάρες barcode (ύψος 64px, module 2px), κωδικό mono letterspaced.
- Πλήρεις λεπτομέρειες: δείτε τα inline styles στο `GeekOn WMS.dc.html` — είναι η πηγή αλήθειας.

## Interactions & Behavior
- **Auto-advance picking**: μετά το τελευταίο τεμάχιο γραμμής → επόμενη γραμμή (toast «Γραμμή ολοκληρώθηκε»)· μετά την τελευταία γραμμή → οθόνη ολοκλήρωσης. Κανένα κουμπί επιβεβαίωσης.
- **Put-away override**: scan διαφορετικής έγκυρης θέσης (pattern `X-NN-NN`) = αποδεκτό, log ως αλλαγή πρότασης.
- **Λάθος scan**: κόκκινο flash + error ήχος + toast με το αναμενόμενο barcode. Δεν προχωράει η ροή.
- **Transitions**: progress bars `transition: width .3s`· toast `translateY(8px)→0, .2s`· flash overlay fade-out.
- Κουμπιά ≥44px ύψος (touch targets), pressed state `transform: scale(.97)`.

## State Management
Ένα state machine με `screen` (login/dash/tasks/search/profile/pick/fill/pickdone/rcv/put/pack/repl/cnt/mov/label) + per-flow sub-state (δείκτης γραμμής, φάση, μετρητές). Κεντρικός dispatcher `onScan(code)` δρομολογεί κάθε barcode ανάλογα με screen+φάση. Στο production τα mock arrays (PICK/RCV/PUT/PACK/CNT/DB) αντικαθίστανται από κλήσεις στο Web API του Mantis LVS.

## Integration με Mantis LVS (σημαντικό)
- Το LVS είναι .NET 3-tier (UI/BL/DA) με MS SQL ή Oracle. Τα RF τερματικά μιλούν με τον RF Communication Server της Mantis· για custom UI ο συνήθης δρόμος είναι **custom Web API layer πάνω στο BL** (ή μέσω του Software Development Enabler / API mechanisms της Mantis — συνεννόηση με τον implementation partner).
- Προτεινόμενα endpoints: auth/login (badge ή PIN), tasks (ανά χρήστη/ζώνη), pick lines, receipts/ASN, putaway proposals (+ override), replenishment/moves, cycle counts (+ διαφορές), stock lookup, label print (ZPL προς εκτυπωτή δικτύου).
- **Scanner**: keyboard wedge με Enter suffix (ρύθμιση στο Honeywell ScanPal/EZConfig). Εναλλακτικά Honeywell Data Intent API σε native app.
- **Offline**: προτείνεται queue αποτυχημένων POST σε localStorage/IndexedDB με retry + εμφανής ένδειξη offline (δεν υλοποιήθηκε στο prototype).
- **Barcode ετικετών**: Code 128 subset B. Στο production η εκτύπωση γίνεται με ZPL template στον printer (π.χ. `^BC` command) — ο αλγόριθμος του prototype χρησιμεύει μόνο για on-screen preview.

## Design Tokens
- **Χρώματα**: brand orange `#ED872D`· dark `#17191E`· φόντο `#F7F5F2` (desk `#ECEAE5`)· λευκές κάρτες `#FFFFFF`· muted text `#9AA0AB`· secondary text `#6B7280`· borders `#E2E5EA` / `#ECEEF2`· tint πορτοκαλί `#FDF1E6`· deep orange text `#C96F1E`· success `#22A55C` (tint `#E6F7EE`)· error `#E05252` / text `#C03D3D` (tint `#FDECEC`)· online LED `#4ADE80`.
- **Τυπογραφία**: Commissioner (400–800) για UI (πλήρης ελληνική υποστήριξη), IBM Plex Mono (500–700) για κωδικούς SKU/θέσεων/μετρητές. Μεγέθη: τίτλοι 19–22px/800, σώμα 13–15px/600–700, labels 10.5–11px/800 letterspacing 1.5–2px, κωδικοί θέσης 36–44px mono/700, hit targets ≥44px.
- **Radius**: κάρτες 16–20px, headers 26px, pill κουμπιά = ύψος/2, chips 8–12px.
- **Σκιές**: κάρτες `0 2px 8px rgba(23,25,30,.05)`· floating `0 6px 18px rgba(23,25,30,.08)`· primary CTA `0 6px 16px rgba(237,135,45,.4)`.

## Assets
- `assets/geekon-logo-on-light.png` — σκούρο wordmark + πορτοκαλί «On»/ρομπότ (για λευκό φόντο)
- `assets/geekon-logo-on-dark.png` — λευκό wordmark (για σκούρο φόντο, χρησιμοποιείται στο Login)
- `assets/geekon-logo-on-orange.png` — λευκό/μαύρο (για πορτοκαλί φόντο)
Προέρχονται από το επίσημο SVG ταμπέλας της GeekOn, με το πορτοκαλί κανονικοποιημένο σε #ED872D. Fonts: Google Fonts (Commissioner, IBM Plex Mono).

## Deployment / Auto-updates στο PDA (προτεινόμενο)
1. Repo στο GitHub με το web app (ή αρχικά με αυτά τα HTML prototypes).
2. **GitHub Pages** (Settings → Pages → deploy from branch ή Actions): κάθε `git push` δημοσιεύει αυτόματα νέα έκδοση σε σταθερό URL.
3. Στο PDA: το URL ως fullscreen shortcut/PWA (kiosk browser όπως Fully Kiosk για lock-down). Κάθε άνοιγμα φορτώνει την τελευταία έκδοση — μηδενικό deployment ανά συσκευή.
4. Για PWA: service worker με `skipWaiting` + version check ώστε το update να περνά και με ανοιχτή την εφαρμογή.

## Files
- `api-contract.yaml` — προτεινόμενο OpenAPI contract για το Web API layer πάνω στο LVS (το Mantis LVS ΔΕΝ έχει δημόσιο REST API — αυτό το contract υλοποιείται από Mantis/partner)
- `GeekOn WMS.dc.html` — κύριο λειτουργικό prototype (template + logic class + mock data)
- `WMS PDA Interface (options).dc.html` — αρχικές 3 κατευθύνσεις σχεδίασης
- `support.js` — runtime για να ανοίγουν τα .dc.html standalone στον browser
- `assets/` — logos
