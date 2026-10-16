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
"""Nyerk24 · Events: pro Event eine Discord-Nachricht, danach nur PATCH.

Erstveröffentlichung ausschließlich mit initial_publish=true im manuellen Workflow.
Nachrichten-IDs bleiben in Events/events_message.json und werden von Actions committet.
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


def response_json(response, context):
    if not response.ok:
        raise RuntimeError(f'{context}: HTTP {response.status_code}: {response.text[:700]}')
    return response.json()


def read_state():
    if not STATE.exists():
        return {}
    data = json.loads(STATE.read_text(encoding='utf-8'))
    if not isinstance(data, dict):
        raise RuntimeError('events_message.json muss ein JSON-Objekt enthalten')
    return data


def save_state(state):
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def publish(event):
    webhook = os.environ['EVENTS_WEBHOOK'].strip().split('?', 1)[0].rstrip('/')
    initial = os.getenv('INITIAL_PUBLISH', 'false').lower() == 'true'
    identity = response_json(requests.get(webhook, timeout=30), 'Webhook abrufen')
    event_id = event.EVENT['id']
    state = read_state()
    stored_id = str(state.get(event_id) or '')
    channel_id = str(identity['channel_id'])
    webhook_id = str(identity['id'])
    bot = requests.Session()
    bot.headers['Authorization'] = 'Bot ' + os.environ['DISCORD_BOT'].strip()

    if stored_id:
        check = bot.get(f'{API}/channels/{channel_id}/messages/{stored_id}', timeout=30)
        if check.status_code == 404:
            if not initial:
                raise RuntimeError('Gespeicherte Eventnachricht wurde gelöscht. Kein neuer Post. Für Neuveröffentlichung initial_publish aktivieren.')
            stored_id = ''
        else:
            msg = response_json(check, 'Gespeicherte Nachricht prüfen')
            if str(msg.get('webhook_id', '')) != webhook_id:
                raise RuntimeError('Gespeicherte Message-ID gehört nicht zum Events-Webhook. Kein Post.')
            if initial:
                raise RuntimeError('Die Eventnachricht existiert bereits. initial_publish ausschalten und normal bearbeiten.')
    elif not initial:
        raise RuntimeError('Noch keine Eventnachrichten-ID vorhanden. Nur die Erstveröffentlichung mit initial_publish=true erlaubt.')

    # Auch beim ersten Start prüfen, ob eine bereits veröffentlichte Nachricht existiert,
    # deren ID wegen eines fehlgeschlagenen Git-Commits nicht gespeichert wurde.
    if initial and not stored_id:
        before = None
        for _ in range(30):
            params = {'limit': 100}
            if before:
                params['before'] = before
            messages = response_json(bot.get(f'{API}/channels/{channel_id}/messages', params=params, timeout=35), 'Sicherheitsprüfung auf vorhandene Events')
            for message in messages:
                if str(message.get('webhook_id', '')) != webhook_id:
                    continue
                attachments = message.get('attachments', [])
                names = {f'{event_id}_banner.png', 'halloween_banner.png'}
                sections = {section['title'] for section in event.EVENT['sections']}
                embeds = message.get('embeds', [])
                if (any(a.get('filename') in names for a in attachments)
                        or any(e.get('title') in sections for e in embeds)
                        or any(n in (e.get('image') or {}).get('url', '') for e in embeds for n in names)):
                    raise RuntimeError('Halloween ist bereits im Kanal vorhanden, aber die ID fehlt. Kein Doppelpost. Vor der Erstveröffentlichung Events-Clear durchführen.')
            if len(messages) < 100:
                break
            before = messages[-1]['id']

    current = event.status()
    payload = event.payload(current)
    filename = f'{event_id}_banner.png'
    payload['attachments'] = [{'id': 0, 'filename': filename}]
    files = {
        'payload_json': (None, json.dumps(payload, ensure_ascii=False)),
        'files[0]': (filename, event.banner(current), 'image/png'),
    }
    url = webhook + (f'/messages/{stored_id}' if stored_id else '')
    result = response_json(requests.request('PATCH' if stored_id else 'POST', url,
                                           params={'wait': 'true'}, files=files, timeout=65),
                           'Discord-Nachricht bearbeiten' if stored_id else 'Erstveröffentlichung')
    message_id = str(result['id'])
    if stored_id and message_id != stored_id:
        raise RuntimeError('Discord hat eine unerwartete Nachrichten-ID geliefert.')
    state[event_id] = message_id
    save_state(state)
    print(f'{event_id}: {"BEARBEITET" if stored_id else "ERSTMALIG ERSTELLT"}; ID {message_id}; Status {current}')
    print('Keine automatische Kanalsuche/Löschung bei normalen Updates; keine neuen Posts ohne initial_publish.')


if __name__ == '__main__':
    publish(load_event())


