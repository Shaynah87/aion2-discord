Ältere Nachrichten werden geladen…
Okay, pass auf. Wir probieren das jetzt einfach und dann entscheiden wir, ob wir es einmal in groß machen mit dem Link da drunter oder ob wir dann wirklich sagen, wir machen es eigentlich wie beim Tracker. Wir komprimieren das ganze Bild. Tatsächlich müssen wir dann halt gucken, ob das mit Datum und angefangen, beendet, bla bla bla, passt oder nicht. Aber ich denke, das ist jetzt aktuell. Gucken wir jetzt einfach mal.

Ja, genau so machen wir es! 😁

Wir testen jetzt erst einmal unser großes Halloween-Banner mit dem anklickbaren Quellenlink direkt darunter.

Das Banner bleibt unverändert. Wir schauen uns die tatsächliche Darstellung in Discord an und entscheiden erst danach, ob wir lieber eine kompaktere Variante wie beim Tracker möchten.

Als Nächstes brauche ich von dir die aktuellen drei Dateien (events.py, halloween.py, events.yml) und die ursprünglichen Halloween-Screenshots.

Dann machen wir alles in einem Durchgang fertig: korrekte Eventinformationen, Quellenlink, automatische Statuswechsel und vor allem die zuverlässige Bearbeitung derselben Discord-Nachricht.

Danach machen wir den Events-Clear und veröffentlichen Halloween einmal sauber neu.

Erst anschauen, dann entscheiden – ohne jetzt schon wieder am Design herumzubasteln.
Eingefügter Text(20261016-145943).txtDokument
"""Nyerk24 · Events: eine dauerhaft gespeicherte Discord-Nachricht je Event.

Die Message-ID wird in Events/events_message.json gespeichert. Der Workflow
committet diese Datei, damit die ID auch beim nächsten Lauf erhalten bleibt.
"""
import importlib.util
import json
import os
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent
STATE = ROOT / 'events_message.json'
API = 'https://discord.com/api/v10'


def load_event():
    path = ROOT / 'Halloween' / 'halloween.py'
    spec = importlib.util.spec_from_file_location('nyerk24_event', path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f'Eventmodul kann nicht geladen werden: {path}')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_state():
    if not STATE.exists():
        return {}
    data = json.loads(STATE.read_text(encoding='utf-8'))
    if not isinstance(data, dict):
        raise RuntimeError('events_message.json muss ein JSON-Objekt sein')
    return data


def save_state(state):
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def api_json(response, context):
    if not response.ok:
        raise RuntimeError(f'{context}: HTTP {response.status_code}: {response.text[:800]}')
    return response.json()


def belongs_to_event(message, webhook_id, event):
    if str(message.get('webhook_id', '')) != str(webhook_id):
        return False
    event_id = event.EVENT['id']
    marker = f'event-id:{event_id}'
    names = {f'{event_id}_banner.png', 'halloween_banner.png'}
    if any(a.get('filename') in names for a in message.get('attachments', [])):
        return True
    embeds = message.get('embeds', [])
    if any(e.get('footer', {}).get('text') == marker for e in embeds):
        return True
    titles = {s['title'] for s in event.EVENT['sections']}
    if sum(e.get('title') in titles for e in embeds) >= 2:
        return True
    return any(any(n in (e.get('image') or {}).get('url', '') for n in names) for e in embeds)


def find_messages(bot, channel_id, webhook_id, event):
    found, before = [], None
    for _ in range(30):
        params = {'limit': 100}
        if before:
            params['before'] = before
        messages = api_json(bot.get(f'{API}/channels/{channel_id}/messages', params=params, timeout=35), 'Nachrichtensuche')
        if not messages:
            break
        found.extend(m['id'] for m in messages if belongs_to_event(m, webhook_id, event))
        before = messages[-1]['id']
        if len(messages) < 100:
            break
    return sorted(set(found), key=int)


def publish(event):
    webhook = os.environ['EVENTS_WEBHOOK'].strip().split('?', 1)[0].rstrip('/')
    token = os.environ['DISCORD_BOT'].strip()
    identity = api_json(requests.get(webhook, timeout=30), 'Webhook-Informationen')
    channel_id, webhook_id = identity['channel_id'], identity['id']
    bot = requests.Session()
    bot.headers['Authorization'] = f'Bot {token}'
    state = read_state()
    event_id = event.EVENT['id']
    stored = str(state.get(event_id, ''))

    # Gespeicherte ID zunächst direkt prüfen. Bei gelöschter Nachricht neu suchen.
    if stored:
        response = bot.get(f'{API}/channels/{channel_id}/messages/{stored}', timeout=30)
        if response.status_code == 404:
            stored = ''
        else:
            message = api_json(response, 'Gespeicherte Nachricht prüfen')
            if not belongs_to_event(message, webhook_id, event):
                raise RuntimeError('Gespeicherte Message-ID gehört nicht zu diesem Events-Webhook/Event; Abbruch ohne neuen Post.')

    # Immer nach weiteren Kopien suchen, auch wenn eine ID gespeichert ist.
    found = find_messages(bot, channel_id, webhook_id, event)
    if stored and stored not in found:
        found.append(stored)
    found = sorted(set(found), key=int)
    message_id = found[0] if found else None

    current = event.status()
    payload = event.payload(current)
    filename = f'{event_id}_banner.png'
    payload['attachments'] = [{'id': 0, 'filename': filename}]
    files = {
        'payload_json': (None, json.dumps(payload, ensure_ascii=False)),
        'files[0]': (filename, event.banner(current), 'image/png'),
    }
    url = webhook + (f'/messages/{message_id}' if message_id else '')
    response = requests.request('PATCH' if message_id else 'POST', url,
                                params={'wait': 'true'}, files=files, timeout=60)
    published = api_json(response, 'Event veröffentlichen/bearbeiten')
    new_id = str(published['id'])
    state[event_id] = new_id
    save_state(state)
    print(f'{event_id}: {"bearbeitet" if message_id else "erstellt"}; ID {new_id}; Status {current}')

    # Ausschließlich eindeutig zugeordnete Doppelposts desselben Webhooks entfernen.
    for duplicate in found:
        if duplicate == new_id:
            continue
        deletion = requests.delete(f'{webhook}/messages/{duplicate}', timeout=35)
        if deletion.status_code not in (204, 404):
            raise RuntimeError(f'Duplikat {duplicate} konnte nicht gelöscht werden: HTTP {deletion.status_code}: {deletion.text[:500]}')
        print(f'Duplikat gelöscht: {duplicate}')
    print('Helper-Nachrichten und andere Events bleiben unberührt.')


if __name__ == '__main__':
    publish(load_event())


name: Events

on:
  workflow_dispatch:

permissions:
  contents: write

concurrency:
  group: halloween-events
  cancel-in-progress: false

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          persist-credentials: true
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Abhängigkeiten installieren
        run: python -m pip install pillow requests
      - name: Halloween-Event synchronisieren
        env:
          DISCORD_BOT: ${{ secrets.DISCORD_BOT }}
          EVENTS_WEBHOOK: ${{ secrets.EVENTS_WEBHOOK }}
        run: python Events/events.py
      - name: Discord-Nachrichten-ID dauerhaft speichern
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git add Events/events_message.json
          if ! git diff --cached --quiet; then
            git commit -m "Store Events Discord message ID [skip ci]"
            git push
          fi
name: Events

on:
  workflow_dispatch:

permissions:
  contents: write

concurrency:
  group: halloween-events
  cancel-in-progress: false

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          persist-credentials: true
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Abhängigkeiten installieren
        run: python -m pip install pillow requests
      - name: Halloween-Event synchronisieren
        env:
          DISCORD_BOT: ${{ secrets.DISCORD_BOT }}
          EVENTS_WEBHOOK: ${{ secrets.EVENTS_WEBHOOK }}
        run: python Events/events.py
      - name: Discord-Nachrichten-ID dauerhaft speichern
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git add Events/events_message.json
          if ! git diff --cached --quiet; then
            git commit -m "Store Events Discord message ID [skip ci]"
            git push
          fi


name: Events

on:
  workflow_dispatch:

permissions:
  contents: write

concurrency:
  group: halloween-events
  cancel-in-progress: false

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          persist-credentials: true
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Abhängigkeiten installieren
        run: python -m pip install pillow requests
      - name: Halloween-Event synchronisieren
        env:
          DISCORD_BOT: ${{ secrets.DISCORD_BOT }}
          EVENTS_WEBHOOK: ${{ secrets.EVENTS_WEBHOOK }}
        run: python Events/events.py
      - name: Discord-Nachrichten-ID dauerhaft speichern
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git add Events/events_message.json
          if ! git diff --cached --quiet; then
            git commit -m "Store Events Discord message ID [skip ci]"
            git push
          fi

Ich habe jetzt die Dateien vorliegen und sehe bereits zwei wichtige Punkte:

Die YAML enthält keinen automatischen Zeitplan. Sie startet ausschließlich über workflow_dispatch. Der Lauf um 15 Uhr wurde also nicht durch einen Zeitplan in dieser YAML ausgelöst.

In der Halloween-Datei steckt noch die alte Button-Logik. Bei bevorstehenden und beendeten Events wird Eventdetails anzeigen eingeblendet. Genau diesen Button wollen wir künftig durch den dauerhaften Quellenlink ersetzen.

Außerdem ist die bisherige events.py unnötig kompliziert: Sie durchsucht bei jedem Lauf den Discord-Kanal nach alten Nachrichten, obwohl wir künftig mit einer gespeicherten Nachrichten-ID arbeiten wollen.

Die Halloween-Datei ist ebenfalls angekommen. Damit habe ich jetzt die drei aktuellen Codegrundlagen.

Ich habe außerdem geprüft: Die hochgeladene Halloween-Datei ist syntaktisch gültig. Das Banner können wir also übernehmen, ohne es neu zu bauen.

Was wir noch ändern müssen, ist klar: den alten Eventdetails-Button entfernen, den offiziellen Link dauerhaft einbauen und die Veröffentlichung so absichern, dass nach unserem geplanten Events-Clear genau eine neue Nachricht erstellt und danach nur noch bearbeitet wird.

Bevor ich die fertigen Dateien erstelle, fehlen mir nur noch die ursprünglichen Halloween-Screenshots. Damit gleiche ich die Belohnungen und Mengen ab. Gerade bei den Süßigkeitenschlüsseln enthält die aktuelle Datei noch den Hinweis auf eine unleserliche Angabe.

Du musst nichts selbst kontrollieren. Schick mir die Screenshots, dann prüfe ich die neun Bereiche und erstelle die vollständigen, aufeinander abgestimmten TXT-Dateien.
Benutzeranhang
Benutzeranhang
Benutzeranhang
Benutzeranhang
Benutzeranhang
Benutzeranhang
Noch was fehlen, sag mir das jetzt bitte.

Ich habe alle sechs Screenshots mit den Daten unserer bisherigen halloween.py verglichen. Die neun Eventbereiche sind damit abgedeckt. Du musst mir keine weiteren Screenshots schicken. 😊

Dabei habe ich Folgendes festgestellt:

    Süßigkeitenschlüssel: Die bisher unleserliche Angabe ist jetzt eindeutig: 1 Umwandlung pro Woche und Server für den roten, gelben und blauen Schlüssel. Den alten Hinweis auf die unleserliche Vorlage entfernen wir.

    Eventshop: Preise und Kauflimits stimmen überein. In unserer Datei fehlen allerdings die erforderlichen Charakterstufen. Die ergänzen wir.

    Eventmissionen: Die Belohnungen stimmen. Der wöchentliche Reset ist ebenfalls bestätigt.

    Anwesenheit, Spezialtruhe, Verbrauchsgegenstände und Süßigkeiteninhalte: Die vorhandenen Angaben stimmen mit deinen Screenshots überein.

    NPC-Händler: Die Standorte aus dem letzten Screenshot fehlen bisher. Die können wir ebenfalls aufnehmen.

Eine Sache fehlt uns noch: die direkte URL zur offiziellen Halloween-Ankündigung. Ich kann sie selbst heraussuchen; du musst sie mir nicht schicken.

Ansonsten haben wir jetzt alles, was wir für die Korrektur brauchen: die Eventdaten, die Python-Dateien, die YAML und unsere festgelegte Veröffentlichungslogik.

Den Events-Clear bitte noch nicht ausführen. Zuerst machen wir die Dateien fertig und prüfen, dass beim ersten Veröffentlichen die Message-ID gespeichert wird und danach ausschließlich diese Nachricht bearbeitet wird.
So eigentlich unten für diese roten, gelben und blauen Süßigkeiten, vielleicht auch Süßigkeiten, die die Farbe haben, oder müssen wir diese großen bunten Punkte nehmen?

Ja! 😁 Ich würde tatsächlich farbige Süßigkeiten statt der großen bunten Punkte nehmen. Das passt viel besser zum Halloween-Event.

Discord unterstützt Emojis direkt in den Embed-Überschriften. Wir könnten beispielsweise diese verwenden:

    🍬 Rote Süßigkeiten – Inhalt

    🍭 Gelbe Süßigkeiten – Inhalt

    🍬 Blaue Süßigkeiten – Inhalt

Allerdings gibt es einen Haken: Die Farbe normaler Emojis lässt sich nicht ändern. Sie sehen je nach Gerät etwas unterschiedlich aus.

Die schönste Lösung wären deshalb drei eigene kleine Discord-Emojis: eine rote, eine gelbe und eine blaue Süßigkeit. Dann hätten wir wirklich die passenden Farben und könnten sie direkt vor die jeweiligen Überschriften setzen.

Mein Vorschlag: Wir nehmen eigene Süßigkeiten-Emojis für diese drei Abschnitte. Das sieht einheitlicher aus als 🔴 🟡 🔵 und passt optisch zum restlichen Halloween-Design.

Dafür müssten wir lediglich drei kleine Emojis auf euren Discord-Server hochladen. Das Banner und die übrige Darstellung bleiben unverändert.
Lass doch einfach die Punkte und dann wir machen einfach nur Süßigkeiten sollen die Leute halt Rot, Gelb und Blau selbst lesen. Oder wir lassen einfach das mit dem Rot, Gelb und blauen Punkt.

Dann lassen wir einfach die bisherigen Punkte! 😁

🔴 Rote Süßigkeiten – Inhalt
🟡 Gelbe Süßigkeiten – Inhalt
🔵 Blaue Süßigkeiten – Inhalt

Das ist eindeutig, übersichtlich und sieht bereits gut aus. Wir müssen nicht für jede Kleinigkeit etwas Neues bauen.

Bleibt also genau so, wie es jetzt ist.
Okay. Brauchst du sonst noch irgendwas? Wenn nicht, gib mir jetzt bitte endlich die Dateien.
1m 4s nachgedacht

Die Screenshots sind abgeglichen, und die Halloween-Datei ist korrigiert. Die farbigen Punkte 🔴 🟡 🔵 bleiben wie gewünscht. Das große Banner bleibt ebenfalls unverändert.

Eine Einschränkung beim Quellenlink: Ich habe die vollständigen Patchnotes mit den Belohnungen gefunden, aber noch keinen verifizierten direkten Link auf der offiziellen AION-2-Webseite. Deshalb verwende ich vorerst einen direkten Link zu einer veröffentlichten Kopie der Patchnotes, statt dir eine falsche offizielle Adresse einzubauen. 
AION 2

Fertig! 😊 Hier sind die drei vollständigen Dateien zum Ersetzen.

1. Events/events.py

Vollständige events.py herunterladen

Erstveröffentlichung mit Sicherheitsprüfung, danach nur noch Bearbeitung derselben Nachricht.

2. Events/Halloween/halloween.py

Vollständige halloween.py herunterladen

Korrigierte Belohnungen, Kauflimits und Stufen, dauerhafter Quellenlink und unverändertes Bannerdesign.

3. .github/workflows/events.yml

Vollständige events.yml herunterladen

Manueller Start mit zusätzlicher Option für die einmalige Erstveröffentlichung. Kein regelmäßiger Zeitplan.

Ich habe beide Python-Dateien auf Syntax geprüft und die drei Darstellungszustände kontrolliert: BEVORSTEHEND = 1 Quellen-Embed, GESTARTET = Quellen-Embed plus 9 Eventbereiche, BEENDET = 1 Quellen-Embed.
So gehen wir jetzt vor

    Alle drei Dateien in GitHub ersetzen und speichern.

    Den bisherigen Halloween-Beitrag über Events-Clear entfernen.

    Den Workflow Events manuell starten und dabei einmalig initial_publish aktivieren.

    Bei späteren Änderungen und beim Cronjob am 04.11.2026 um 09:00 Uhr bleibt initial_publish deaktiviert.

Die Dateien sind vorbereitet, aber noch nicht live gegen Discord getestet. Das ist unser nächster Schritt.

Wichtig: Der hinterlegte Link führt vorerst zu den vollständigen Event-Patchnotes auf Patchbot, nicht direkt zur offiziellen AION-2-Webseite. Den direkten offiziellen Link können wir später austauschen, ohne das Layout zu verändern.

"""Halloween 2026: feste Daten, Bannerdesign und Discord-Darstellung.

Änderungen am Event erfolgen hier; keine automatische Inhaltsbeschaffung.
Die zentrale events.py kümmert sich ausschließlich um das Veröffentlichen.
"""
import io
import random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

from datetime import datetime
from zoneinfo import ZoneInfo

EVENT = {
    "id": "halloween_2026",
    "name": "Halloween",
    "timezone": "Europe/Berlin",
    "start": "2026-10-14T00:00:00+02:00",  # Datum bekannt, genaue Wartungszeit nicht angegeben
    "end": "2026-11-04T09:00:00+01:00",
    "date_label": "14.10. – 04.11.2026",
    "image": "Events/Halloween/halloween.png",
    "currency": "Halloween-Kürbismünze (Event)",
    "source_url": "https://patchbot.io/games/aion-2/articles/1777-notice-patch-notes-oct-13-pdt-oct-14-cest",
    "sections": [
        {
            "title": "🎃 Süßes oder Saures – Anwesenheit",
            "description": "Tägliche Anmeldung über das Eventmenü. Belohnung: Halloween-Kürbismünzen (Event).",
            "entries": [
                {"days": "1–6", "coins_per_day": 35},
                {"days": "7", "coins_per_day": 100},
                {"days": "8–13", "coins_per_day": 35},
                {"days": "14", "coins_per_day": 100},
            ],
        },
        {
            "title": "⚔️ Saisonmissionen – Event",
            "description": "Im Spiel unter [Saisonmission] > [Event]. Einmal pro Woche pro Server. Belohnungen jeweils in Halloween-Kürbismünzen (Event).",
            "entries": [
                {"name": "Abyssus", "task": "10 Monster im Abyssus jagen", "coins": 25},
                {"name": "Transzendenz", "task": "1-mal den Transzendenz-Dungeon abschließen", "coins": 25},
                {"name": "Expedition", "task": "1-mal die Expeditions-Eroberung abschließen", "coins": 25},
                {"name": "Aszensusritus", "task": "1-mal den Aszensusritus abschließen", "coins": 25},
                {"name": "Albtraum", "task": "1-mal abschließen (beliebige Stufe)", "coins": 25},
                {"name": "Anmelden", "task": "3-mal anmelden", "coins": 30},
                {"name": "Ausrüstung erhalten", "task": "1 einzigartiges Ausrüstungsteil erhalten", "coins": 20},
                {"name": "Schriftrolle benutzen", "task": "5 Schriftrollen benutzen", "coins": 20},
                {"name": "Dimensionale Invasion", "task": "1-mal an der Dimensionalen Invasion teilnehmen", "coins": 20},
                {"name": "Shugofesta", "task": "1-mal an der Shugofesta teilnehmen", "coins": 20},
            ],
        },
        {
            "title": "🛍️ Halloween-Eventshop",
            "description": "Beim Event-Münzhändler: Elyos – Verteron (Basis der Legion der Morgenröte / Zumionstätte); Asmodier – Altgard (Exulantendorf / Nornirkonvent). Preise in Halloween-Kürbismünzen (Event); Menge je Kauf: 1.",
            "entries": [
                {"name": "Halloween-Spezialtruhe", "price": 250, "limit": "1 pro Server", "level": 10},
                {"name": "Odenergie (Gebunden)", "price": 10, "limit": "4 pro Server/Woche", "level": 45},
                {"name": "Abyss-Rissstein: Untere Ebene (Gebunden)", "price": 30, "limit": "2 pro Server/Woche", "level": 45},
                {"name": "Skin-Truhe (10x) (Gebunden)", "price": 15, "limit": "5 pro Server/Woche", "level": 10},
                {"name": "Geiststein der Wiederbelebung (Gebunden)", "price": 2, "limit": "10 pro Server/Woche", "level": 10},
                {"name": "Sofortabschluss-Ticket: Täglicher Dungeon (Gebunden)", "price": 3, "limit": "7 pro Server/Woche", "level": 10},
                {"name": "Herausforderungsticket: Albtraum-Dungeon (Gebunden)", "price": 7, "limit": "3 pro Server/Woche", "level": 10},
                {"name": "Shugofesta-Schlüssel (Gebunden)", "price": 7, "limit": "3 pro Server/Woche", "level": 10},
                {"name": "Lebenskristall (Gebunden)", "price": 2, "limit": "20 pro Charakter", "level": 10},
                {"name": "Halloween-Süßigkeiten (Gebunden)", "price": 2, "limit": "10 pro Charakter", "level": 10},
                {"name": "Halloween-Keks (Gebunden)", "price": 2, "limit": "10 pro Charakter", "level": 10},
                {"name": "Hochwertiger Siegelstein (Gebunden)", "price": 1, "limit": "Keine angegebene Begrenzung", "level": 10},
            ],
        },
        {
            "title": "🎁 Halloween-Spezialtruhe",
            "entries": [
                {"name": "Gruseliges Skelett (Skin: Brustpanzer) (Gebunden)", "quantity": 1},
                {"name": "Pet-Seelenkristall", "quantity": 10000},
            ],
        },
        {
            "title": "🍬 Verbrauchsgegenstände",
            "entries": [
                {"name": "Halloween-Süßigkeiten (Gebunden)", "duration": "5 Minuten", "effects": ["Angriffskraft +25", "Verteidigung +250", "Max. SP +300", "Natürliche SP-Erholung +40 %"]},
                {"name": "Halloween-Keks (Gebunden)", "duration": "5 Minuten", "effects": ["Max. LP +500", "Max. MP +250", "Max. SP +300", "Natürliche SP-Erholung +40 %"]},
            ],
        },
        {
            "title": "🔑 Süßigkeitenschlüssel – Umwandlung",
            "description": "Süßigkeitenschlüssel-Fragmente (Event) erhältst du bei Expeditions- und Transzendenz-Zusammenstößen. Erfolgsrate aller Umwandlungen: 100 %. Rote, gelbe und blaue Schlüssel: jeweils einmal pro Woche pro Server.",
            "entries": [
                {"name": "Roter Süßigkeitenschlüssel (Event)", "quantity": 1, "fragments": 60},
                {"name": "Gelber Süßigkeitenschlüssel (Event)", "quantity": 1, "fragments": 60},
                {"name": "Blauer Süßigkeitenschlüssel (Event)", "quantity": 1, "fragments": 60},
                {"name": "Hochwertiger Siegelstein (Gebunden)", "quantity": 10, "fragments": 1},
            ],
        },
        {
            "title": "🔴 Rote Süßigkeiten – Inhalt",
            "entries": [
                {"name": "Pet-Truhe des Wachstums (Gebunden)", "quantity": 20},
                {"name": "Rolle der Kampf-Verstärkung (Gebunden)", "quantity": 10},
                {"name": "Halloween-Süßigkeiten (Gebunden)", "quantity": 5},
                {"name": "Halloween-Keks (Gebunden)", "quantity": 5},
            ],
        },
        {
            "title": "🟡 Gelbe Süßigkeiten – Inhalt",
            "entries": [
                {"name": "Abysspunkte", "quantity": 10000},
                {"name": "Lebenskristall (Gebunden)", "quantity": 10},
                {"name": "Halloween-Süßigkeiten (Gebunden)", "quantity": 5},
                {"name": "Halloween-Keks (Gebunden)", "quantity": 5},
            ],
        },
        {
            "title": "🔵 Blaue Süßigkeiten – Inhalt",
            "entries": [
                {"name": "Odenergie (Gebunden)", "quantity": 4},
                {"name": "Geiststein der Wiederbelebung (Gebunden)", "quantity": 10},
                {"name": "Halloween-Süßigkeiten (Gebunden)", "quantity": 5},
                {"name": "Halloween-Keks (Gebunden)", "quantity": 5},
            ],
        },
    ],
}


def status(now=None):
    """Gibt 'upcoming', 'active' oder 'finished' zurück."""
    tz = ZoneInfo(EVENT["timezone"])
    now = now.astimezone(tz) if now is not None else datetime.now(tz)
    start = datetime.fromisoformat(EVENT["start"]).astimezone(tz)
    end = datetime.fromisoformat(EVENT["end"]).astimezone(tz)
    if now < start:
        return "upcoming"
    if now < end:
        return "active"
    return "finished"


if __name__ == "__main__":
    print(f'{EVENT["name"]}: {status()}')


# ===== HALLOWEEN-BANNER UND DISCORD-INHALT =====

def font(size, bold=True):
    choices = ([
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
    ] if bold else [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ])
    for path in choices:
        if Path(path).is_file():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def banner(current):
    # Identisches Bannerformat bei allen Status, angelehnt an die Content-Header.
    width, height = 1200, 220
    source = Image.open(Path(__file__).resolve().parent / "halloween.png").convert("RGB")
    factor = max(width / source.width, height / source.height)
    source = source.resize((round(source.width * factor), round(source.height * factor)), Image.Resampling.LANCZOS)
    left = (source.width - width) // 2
    top = (source.height - height) // 2
    base = source.crop((left, top, left + width, top + height)).convert("RGBA")

    # Lesbarkeit: sanfter dunkler Mittelbereich, ohne die Randmotive zu verdecken.
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    alpha = Image.new("L", (width, height), 0)
    px = alpha.load()
    for x in range(width):
        strength = max(0.0, 1.0 - abs(x - width / 2) / (width * 0.43))
        value = int(135 * (strength ** 0.65))
        for y in range(height):
            px[x, y] = value
    overlay.putalpha(alpha.filter(ImageFilter.GaussianBlur(22)))
    base = Image.alpha_composite(base, overlay)

    labels = {"upcoming": "BALD VERFÜGBAR", "active": "GESTARTET", "finished": "BEENDET"}
    title = EVENT["name"].upper()
    subtitle = f'{EVENT["date_label"]} · {labels[current]}'
    draw = ImageDraw.Draw(base)
    title_font = font(49)
    subtitle_font = font(31)
    # Exakte Compact-Typografie aus Content/Launch/launch.py:
    # 1200 x 220, Titel 49 px, Status 31 px, Buchstabenabstand 5 px,
    # Abstand 18 px, vertikal anhand sichtbarer Glyphen zentriert.
    title_spacing = 5
    title_box = draw.textbbox((0, 0), title, font=title_font)
    sub_box = draw.textbbox((0, 0), subtitle, font=subtitle_font)
    title_height = title_box[3] - title_box[1]
    sub_height = sub_box[3] - sub_box[1]
    gap = 18
    top_y = (height - (title_height + gap + sub_height)) / 2

    # Feuerorange mit eingebrannten dunklen Adern INNERHALB der Buchstaben.
    # Keine dicke schwarze Außenkontur: Die Textmaske begrenzt alle Strukturen.
    def ember_text(value, face, y, seed, subtitle=False, spacing=0):
        bounds = draw.textbbox((0, 0), value, font=face)
        total_width = sum(draw.textlength(ch, font=face) for ch in value) + max(0, len(value) - 1) * spacing
        x = (width - total_width) / 2
        text_y = int(y - bounds[1])
        mask = Image.new("L", (width, height), 0)
        mask_draw = ImageDraw.Draw(mask)
        for index, ch in enumerate(value):
            mask_draw.text((x, text_y), ch, font=face, fill=255)
            x += draw.textlength(ch, font=face)
            if index < len(value) - 1:
                x += spacing
        bbox = mask.getbbox()
        if not bbox:
            return

        # Nur ein zurückhaltender Schein HINTER der Schrift.
        glow = Image.new("RGBA", (width, height), (255, 85, 0, 0))
        blurred = mask.filter(ImageFilter.GaussianBlur(11 if not subtitle else 6))
        glow.putalpha(blurred.point(lambda a: int(a * (0.53 if not subtitle else 0.25))))
        base.alpha_composite(glow)

        # Verlauf vollständig IN der Schrift: helle Glut oben, tiefes Orange unten.
        fill_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        pixels = fill_layer.load()
        top, bottom = bbox[1], max(bbox[3], bbox[1] + 1)
        for py in range(top, bottom):
            t = (py - top) / (bottom - top)
            if subtitle:
                color = (255, int(186 - 65*t), int(65 - 42*t), 255)
            elif t < 0.40:
                f = t / 0.40
                color = (255, int(179 - 83*f), int(35 - 28*f), 255)
            else:
                f = (t - 0.40) / 0.60
                color = (int(255 - 28*f), int(96 - 57*f), int(7 - 7*f), 255)
            for px in range(bbox[0], bbox[2]):
                pixels[px, py] = color
        fill_layer.putalpha(mask)
        base.alpha_composite(fill_layer)

        if not subtitle:
            # Schwarze, unregelmäßige Brandadern, ausschließlich in den Glyphen.
            rng = random.Random(seed)
            crack_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            cracks = ImageDraw.Draw(crack_layer)
            for _ in range(35):
                cx = rng.randint(bbox[0], bbox[2] - 1)
                cy = rng.randint(bbox[1], bbox[3] - 1)
                length = rng.randint(7, 24)
                points = [(cx, cy)]
                for step in range(3):
                    cx += rng.randint(-7, 7)
                    cy += max(1, length // 3) + rng.randint(-2, 2)
                    points.append((cx, cy))
                cracks.line(points, fill=(22, 5, 3, rng.randint(145, 215)), width=rng.choice((1, 2, 2, 3)))
            crack_alpha = Image.composite(crack_layer.getchannel("A"),
                                          Image.new("L", (width, height), 0), mask)
            crack_layer.putalpha(crack_alpha)
            base.alpha_composite(crack_layer)

    ember_text(title, title_font, top_y, seed=20261014, spacing=title_spacing)
    ember_text(subtitle, subtitle_font, top_y + title_height + gap,
               seed=20261104, subtitle=True)
    result = io.BytesIO()
    base.convert("RGB").save(result, format="PNG", optimize=True)
    return result.getvalue()


def entry_line(entry):
    """Einheitliche, kompakte Zeilen mit klar erkennbarer Belohnung."""
    if "days" in entry:
        return f'• **Tag {entry["days"]}**  —  **{entry["coins_per_day"]} Münzen/Tag**'
    name = entry.get("name", "")
    if "task" in entry:
        return f'• {name}: {entry["task"]}  →  **{entry["coins"]} Münzen**'
    if "price" in entry:
        return f'• **{name}**  —  **{entry["price"]} Münzen**\n  ↳ {entry["limit"]} · ab Stufe {entry["level"]}'
    if "fragments" in entry:
        return f'• {name} ×{entry["quantity"]}  —  **{entry["fragments"]} Fragmente**'
    if "effects" in entry:
        effects = " · ".join(entry["effects"])
        return f'• **{name}** ({entry["duration"]})\n  ↳ {effects}'
    qty = f'{entry.get("quantity", 1):,}'.replace(",", ".")
    return f'• {name}  —  **×{qty}**'


def detail_embeds():
    """Neun übersichtliche Abschnitte; die Daten bleiben unverändert."""
    embeds = []
    for section in EVENT["sections"]:
        lines = []
        if section.get("description"):
            lines.extend((section["description"], ""))
        lines.extend(entry_line(entry) for entry in section["entries"])
        description = "\n".join(lines)
        if len(description) > 4096:
            raise ValueError(f'Eventabschnitt zu lang: {section["title"]}')
        embeds.append({
            "title": section["title"],
            "description": description,
            "color": 0xFF7100,
        })
    return embeds


def payload(current):
    """Großes Banner als Anhang, Quellen-Embed und Details nur während des Events."""
    source = EVENT["source_url"]
    if not source.startswith("https://"):
        raise ValueError("Gültige HTTPS-Quellen-URL fehlt")
    link = {
        "title": "🔗 Eventankündigung & Belohnungen ansehen",
        "url": source,
        "description": "Patchnotes und ursprüngliche Belohnungstabellen öffnen ↗",
        "color": 0xFF7100,
    }
    embeds = [link] + (detail_embeds() if current == "active" else [])
    if len(embeds) > 10:
        raise ValueError("Discord erlaubt maximal 10 Embeds")
    if sum(len(e.get("title", "")) + len(e.get("description", "")) for e in embeds) > 6000:
        raise ValueError("Discord erlaubt maximal 6000 Zeichen in allen Embeds")
    return {"embeds": embeds, "components": [], "allowed_mentions": {"parse": []}}


