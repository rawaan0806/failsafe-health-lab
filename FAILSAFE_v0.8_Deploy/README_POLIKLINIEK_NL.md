# FAILSAFE v1.1 — Polikliniekdemo

Nieuwe demo: **Polikliniek / Outpatient Clinic Lab**. De rustige homepage leidt nu naar `outpatient.html`.

## Wat kun je invullen?

1. Patiënten en bezoeken: aantal patiënten, openingstijden, soorten bezoeken, aandeel verpleegkundige intake, auto/parkeren.
2. Personeel: algemene artsen, specialisten, verpleegkundigen, balie en diagnostisch personeel.
3. Faciliteiten: spreekkamers, diagnoseruimtes, apparaten, parkeervakken.
4. Budget: fictief dagelijks verbeterbudget in euro en optionele voorbeeldkosten.
5. Controle en analyse: controleer de ingevoerde getallen en klik **Run clinic analysis**.

De rapportpagina laat simulatie-uitkomsten, mogelijke knelpunten en maximaal twee voorgestelde uitbreidingen binnen het opgegeven voorbeeldbudget zien.

**Let op:** Deze applicatie maakt een **fictieve eendaagse capaciteitssimulatie**. Patiënttypen en tijden zijn verzonnen. Er worden geen echte diagnoses, dienstenroosters, medische prioriteiten of klinische veiligheidsrisico's voorspeld. De bedragen in euro zijn slechts invulbare aannames. Er zijn **geen werkelijke ziekenhuisgegevens** nodig. De optimizer is een exacte vergelijkingsmethode, geen getraind klinisch AI-model.

## Op Windows

Pak `FAILSAFE_v1.1_Polikliniek_Complete.zip` uit. Open `FAILSAFE_v0.8_Deploy` en dubbelklik `START_FAILSAFE_WINDOWS.bat`. Deze probeert `py`, `python` of `uv` te gebruiken. Ga naar `http://127.0.0.1:8765/outpatient` als de browser niet automatisch opent.

**Zonder Python:** Dubbelklik op `outpatient.html` in de uitgepakte map om de vragenlijst en de vormgeving te bekijken. Nieuwe uitkomsten berekenen kan alleen als de Python-server draait.

## Bestaande Render-site bijwerken

De GitHub-repository bevat al de map `FAILSAFE_v0.8_Deploy`. Upload de gewijzigde bestanden naar dezelfde paden **binnen deze map**. Let op dat `assets/outpatient.css` en `assets/outpatient.js` onder `assets` komen. Na commit zal Render de nieuwe code opnieuw publiceren. Controleer daarna `/outpatient` en de knop op de homepage.

**Er is nog niets gewijzigd op je bestaande publieke site totdat je deze bestanden uploadt.**


## v1.2: Aantallen, parkeren en de hoofdpagina
- De homepage (`index.html`) legt nu uit wat FAILSAFE doet en leidt bezoekers naar de polikliniekdemo.
- Bij patiënten worden aantallen ingevuld in plaats van percentages. De app berekent specialistische afspraken als restant. Verpleegkundige intake en aankomst per auto mogen overlappen met de afspraaktypes.
- Bij parkeren vraagt de demo naar de totale fysieke parkeercapaciteit en hoeveel plekken gedurende de gesimuleerde dag niet beschikbaar zijn voor deze patiënten. Het resterende aantal is modelmatig beschikbaar. Parkeerplaatsen worden per auto hergebruikt zodra het virtuele bezoek is afgerond.
- Er bestaat geen vast landelijk maximumaantal parkeerplaatsen; de huidige interface hanteert 0–1000 uitsluitend als veilige technische invoergrens.
- De simulatie blijft een fictief onderwijsexperiment, niet geschikt voor echte ziekenhuisbeslissingen.

## v1.3: Random seed onder geavanceerde instellingen

De optionele random seed staat nu in een dichtgeklapt paneel 'Advanced settings (optional)'. Leeg laten gebruikt automatisch seed 42. De gewone vragenlijst vraagt alleen het voorbeeldbudget.
