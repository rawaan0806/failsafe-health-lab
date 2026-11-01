# FAILSAFE online publiceren — stappenplan (Nederlands)

**Status:** dit pakket is klaar om te deployen, maar er is nog geen publieke website aangemaakt. Je moet zelf toegang geven tot je GitHub- en Render-accounts. De simulator blijft volledig synthetisch, zonder echte patiëntgegevens.

## 1. Bestanden naar GitHub

1. Ga naar https://github.com/new en log in (maak zo nodig een gratis account).
2. Repository name: `failsafe-health-lab`. Kies **Public** als je wilt dat de jury de code kan lezen, of Private als je die voorlopig wilt afschermen. Voeg bij aanmaken geen README/.gitignore/license toe: die zitten al in het pakket.
3. Klik **Create repository**.
4. Klik in de lege repository op **uploading an existing file** (of Add file > Upload files).
5. Open de uitgepakte map `FAILSAFE_v0.8_Deploy` op je computer. Selecteer de **bestanden en mappen IN deze map** en sleep ze naar de GitHub-uploadpagina. Dus niet de ZIP als één bestand toevoegen. Let erop dat de map `assets/` met zijn bestanden wordt meegenomen en dat `app.py`, `render.yaml`, `requirements.txt`, `index.html`, `lab.html`, `server.py` in de hoofdmap terechtkomen.
6. Controleer bij voorkeur ook dat het verborgen bestand `.python-version` is geüpload (Render kan ook handmatig op Python 3.12 worden ingesteld).
7. Klik **Commit changes** / **Commit files**.

Alternatief: gebruik GitHub Desktop om een bestaande lokale projectmap te publiceren; deze methode is soms gemakkelijker voor mappen en latere updates.

## 2. Render-webservice maken

1. Ga naar https://dashboard.render.com en log in.
2. Kies **New > Web Service**, en verbind je GitHub-account als daarom wordt gevraagd.
3. Kies repository `failsafe-health-lab`.
4. Configureer de webservice:
   - **Name**: `failsafe-health-lab` (of een beschikbare variant)
   - **Language/Runtime**: `Python 3`
   - **Branch**: `main`
   - **Root Directory**: leeg laten (code staat in de hoofdmap)
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --threads 3 --timeout 120 --access-logfile -`
   - **Instance type**: `Free`, als beschikbaar
5. Klik **Create Web Service** of **Deploy Web Service**.
6. Bekijk de **Deploy logs**. Wanneer de status **Live** verschijnt, krijg je bovenaan een publieke URL met `.onrender.com`. De gekozen naam is niet gegarandeerd beschikbaar.

Je kunt in plaats van de handmatige instelling ook een **Blueprint** instellen met het meegeleverde `render.yaml`, als je al weet hoe Render Blueprints werken. Gebruik niet beide methoden tegelijk voor dezelfde webservice.

## 3. Controleer je publieke website

Vervang `JOUW-LINK` door de URL die Render daadwerkelijk toont:

- `https://JOUW-LINK.onrender.com/` — homepage.
- `https://JOUW-LINK.onrender.com/lab` — interactieve simulatie.
- `https://JOUW-LINK.onrender.com/health` — moet `{"ok":true,...}` tonen.

Doe deze browsertest:
1. Open de homepage in een privévenster.
2. Klik **Launch interactive demo**.
3. Klik **Run live stress test** en controleer of de cijfers verschijnen.
4. Klik **Try overload** en bekijk de tijdlijn van patiënten.
5. Test ook op je telefoon en in een andere browser.

**Belangrijk:** De eerste pagina kan bij gratis hosting na 15 minuten inactiviteit circa een minuut nodig hebben om op te starten. De server bewaart geen simulatiegegevens en gebruikt geen echte medische dossiers. Gebruik de resultaten nooit voor medische beslissingen.

## 4. Problemen oplossen

- **Build failed**: kijk of `requirements.txt` in de hoofdmap van GitHub staat; kijk in Render Deploy Logs.
- **ModuleNotFoundError**: waarschijnlijk staat code in een extra onderliggende map. Zet `Root Directory` naar die map, of verplaats bestanden naar de repository-hoofdmap.
- **No open ports detected**: controleer de startopdracht met `--bind 0.0.0.0:$PORT`.
- **Homepage werkt, simulatie niet**: controleer of je **Web Service** hebt gekozen, niet **Static Site**; open `/health` en Render Logs.
- **503 of 429**: de publieke demo is tijdelijk druk. Probeer opnieuw; er is een eenvoudige limiet ingesteld om misbruik en overbelasting te beperken.

## 5. Volgende stap na publicatie

Kopieer je echte Render-link en stuur die in deze chat. Dan controleren we de website en bereiden we de demovideo voor.
