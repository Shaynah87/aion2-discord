import os
import json
import re
import html
import time
import hashlib
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime

DISCORD_WEBHOOK = os.environ.get('ANKUENDIGUNGEN_WEBHOOK')
API_ROOT = 'https://api-global-community.plaync.com/aion2_global/board/notice_de'
BOARD_API = API_ROOT
LIST_API = API_ROOT + '/article/search/moreArticle?isVote=true&moreSize=18&moreDirection=BEFORE&previousArticleId=0'
BASE_DIR = Path(__file__).resolve().parent
STATE_FILE = BASE_DIR / 'ankuendigungen_status.json'
DELETION_CONFIRMATIONS = 2


def request_json(url, method='GET', payload=None):
    data = json.dumps(payload, ensure_ascii=False).encode('utf-8') if payload is not None else None
    headers = {'User-Agent': 'AION2-Discord-Bot', 'Accept': 'application/json'}
    if data is not None:
        headers['Content-Type'] = 'application/json'
    for attempt in range(5):
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                body = response.read()
                return json.loads(body.decode('utf-8')) if body else {}
        except urllib.error.HTTPError as error:
            if error.code == 429 or 500 <= error.code < 600:
                if attempt < 4:
                    retry = error.headers.get('Retry-After')
                    try:
                        delay = float(retry) if retry else 2 ** attempt
                    except ValueError:
                        delay = 2 ** attempt
                    time.sleep(max(1, min(delay, 60)))
                    continue
            raise
        except (urllib.error.URLError, TimeoutError):
            if attempt == 4:
                raise
            time.sleep(2 ** attempt)


def discord_url(message_id=None, wait=False):
    base = DISCORD_WEBHOOK.rstrip('/')
    if message_id is not None:
        return f'{base}/messages/{message_id}'
    return base + ('?wait=true' if wait else '')


def discord_create(embed):
    return request_json(discord_url(wait=True), 'POST', {
        'embeds': [embed], 'allowed_mentions': {'parse': []}
    })


def discord_edit(message_id, embed):
    return request_json(discord_url(message_id), 'PATCH', {
        'embeds': [embed], 'allowed_mentions': {'parse': []}
    })


def discord_delete(message_id):
    return request_json(discord_url(message_id), 'DELETE')


def find_images(value):
    if not isinstance(value, str):
        return []
    result = []
    for image in re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', value, re.I):
        image = html.unescape(image)
        if image.startswith('//'):
            image = 'https:' + image
        if image not in result:
            result.append(image)
    return result


def image_dimensions(url):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=20) as response:
            data = response.read(200000)
        if data.startswith(b'\x89PNG') and len(data) >= 24:
            return int.from_bytes(data[16:20], 'big'), int.from_bytes(data[20:24], 'big')
        if data.startswith(b'\xff\xd8'):
            index = 2
            while index < len(data) - 9:
                if data[index] != 0xff:
                    index += 1
                    continue
                marker = data[index + 1]
                if marker in (0xc0, 0xc1, 0xc2, 0xc3, 0xc5, 0xc6, 0xc7, 0xc9, 0xca, 0xcb, 0xcd, 0xce, 0xcf):
                    return int.from_bytes(data[index + 7:index + 9], 'big'), int.from_bytes(data[index + 5:index + 7], 'big')
                length = int.from_bytes(data[index + 2:index + 4], 'big')
                if length < 2:
                    break
                index += 2 + length
    except Exception as error:
        print(f'Bildgröße nicht lesbar: {error}')
    return None


def choose_preview_image(images):
    for image in images:
        dimensions = image_dimensions(image)
        if dimensions:
            width, height = dimensions
            if height > 0 and width >= 500 and height >= 250 and 1.4 <= width / height <= 4:
                return image
    return None


def format_date(item):
    raw = (item.get('timestamps') or {}).get('postDateTime', '')
    if not raw:
        return ''
    try:
        return datetime.fromisoformat(raw.replace('Z', '+00:00')).strftime('%d.%m.%Y')
    except (ValueError, TypeError):
        return str(raw)[:10]


def load_state():
    if not STATE_FILE.exists():
        return {'posted_article_ids': [], 'managed': {}}
    with STATE_FILE.open('r', encoding='utf-8') as file:
        data = json.load(file)
    if not isinstance(data, dict):
        raise ValueError('Ungültige Statusdatei')
    data.setdefault('posted_article_ids', [])
    data.setdefault('managed', {})
    if not isinstance(data['managed'], dict) or not isinstance(data['posted_article_ids'], list):
        raise ValueError('Ungültiges Format der Statusdatei')
    return data


def save_state(state):
    temp = STATE_FILE.with_suffix('.json.tmp')
    with temp.open('w', encoding='utf-8') as file:
        json.dump(state, file, ensure_ascii=False, indent=2)
    os.replace(temp, STATE_FILE)


def article_detail(article_id):
    data = request_json(f'{API_ROOT}/article/{article_id}')
    article = data.get('article')
    if not isinstance(article, dict):
        raise ValueError(f'Artikel {article_id}: API liefert keine Artikeldaten')
    content = article.get('content') or {}
    if not isinstance(content, dict):
        raise ValueError(f'Artikel {article_id}: ungültiger Inhalt')
    return article, str(content.get('content') or '')


def make_embed(item, raw_content, preview_image):
    article_id = item['id']
    title = item.get('title') or 'Neue AION 2 Ankündigung'
    date = format_date(item)
    description = '📢 **Offizielle AION 2 Ankündigung**'
    if date:
        description += f'\nVeröffentlicht am **{date}**'
    embed = {
        'title': title[:256],
        'url': f'https://aion2.plaync.com/de-de/board/notice/view?articleId={article_id}',
        'description': description,
        'color': 4231679
    }
    if preview_image:
        embed['image'] = {'url': preview_image}
    return embed


def fingerprint(item, raw_content):
    relevant = {
        'title': item.get('title'),
        'timestamps': item.get('timestamps'),
        'content': raw_content
    }
    serialized = json.dumps(relevant, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(serialized.encode('utf-8')).hexdigest()


def main():
    if not DISCORD_WEBHOOK:
        raise RuntimeError('ANKUENDIGUNGEN_WEBHOOK fehlt.')

    # Bei API-Fehlern NICHTS als gelöscht behandeln.
    request_json(BOARD_API)
    listing = request_json(LIST_API)
    articles = listing.get('contentList')
    if not isinstance(articles, list) or not articles:
        print('Keine gültige Artikelliste erhalten – keine Änderungen.')
        return
    if any(not isinstance(a, dict) or a.get('id') is None for a in articles):
        print('Unvollständige Artikelliste – keine Änderungen.')
        return

    state = load_state()
    legacy_ids = {str(value) for value in state['posted_article_ids']}
    managed = state['managed']
    listed = {str(article['id']): article for article in articles}
    print(f'{len(articles)} offizielle Ankündigungen gefunden.')

    # Die Liste enthält nur die neuesten 18 Artikel. Ältere Beiträge
    # dürfen daher NICHT wegen Abwesenheit gelöscht werden.
    numeric_ids = []
    for article in articles:
        try:
            numeric_ids.append(int(article['id']))
        except (TypeError, ValueError):
            numeric_ids = []
            break
    oldest_visible = min(numeric_ids) if numeric_ids else None

    # Alt -> neu, damit die Discord-Reihenfolge stimmt.
    for item in reversed(articles):
        article_id = str(item['id'])
        record = managed.get(article_id)
        if not record and article_id in legacy_ids:
            # Vorherige Bot-Version hat keine Discord-Nachrichten-IDs gespeichert.
            continue
        try:
            detail, raw_content = article_detail(article_id)
            # Listeneintrag ist maßgeblich für Titel und Datum, Detail liefert Inhalt.
            digest = fingerprint(item, raw_content)
            if record and record.get('hash') == digest:
                if record.get('missing_checks'):
                    record['missing_checks'] = 0
                    save_state(state)
                continue

            preview = choose_preview_image(find_images(raw_content))
            embed = make_embed(item, raw_content, preview)

            if record:
                discord_edit(record['discord_message_id'], embed)
                record['hash'] = digest
                record['missing_checks'] = 0
                record['title'] = item.get('title', '')
                print(f'Aktualisiert: {embed["title"]}')
            else:
                response = discord_create(embed)
                message_id = response.get('id')
                if not message_id:
                    raise RuntimeError('Discord hat keine Nachrichten-ID zurückgegeben')
                managed[article_id] = {
                    'discord_message_id': str(message_id),
                    'hash': digest,
                    'missing_checks': 0,
                    'title': item.get('title', '')
                }
                if article_id not in legacy_ids:
                    state['posted_article_ids'].append(item['id'])
                    legacy_ids.add(article_id)
                print(f'Neu gepostet: {embed["title"]}')
            save_state(state)
        except Exception as error:
            print(f'Artikel {article_id} nicht verarbeitet: {error}')
            # Einzelner Fehler darf andere Artikel nicht blockieren.

    # Nur eindeutig innerhalb des sichtbaren Listenfensters fehlende
    # Artikel gelten als mögliche Löschungen. Zwei getrennte Durchläufe
    # müssen das Fehlen bestätigen.
    for article_id, record in list(managed.items()):
        if article_id in listed:
            if record.get('missing_checks'):
                record['missing_checks'] = 0
                save_state(state)
            continue
        if oldest_visible is None:
            continue
        try:
            if int(article_id) < oldest_visible:
                continue
        except ValueError:
            continue
        record['missing_checks'] = record.get('missing_checks', 0) + 1
        if record['missing_checks'] < DELETION_CONFIRMATIONS:
            print(f'Fehlende Meldung {article_id}: erste Bestätigung, noch nicht gelöscht.')
            save_state(state)
            continue
        try:
            discord_delete(record['discord_message_id'])
            print(f'Aus Discord entfernt: {record.get("title", article_id)}')
            del managed[article_id]
            state['posted_article_ids'] = [
                value for value in state['posted_article_ids']
                if str(value) != article_id
            ]
            save_state(state)
        except urllib.error.HTTPError as error:
            if error.code == 404:
                # Die Discord-Nachricht wurde bereits manuell gelöscht.
                del managed[article_id]
                state['posted_article_ids'] = [
                    value for value in state['posted_article_ids']
                    if str(value) != article_id
                ]
                save_state(state)
            else:
                print(f'Löschen fehlgeschlagen ({article_id}): {error}')
        except Exception as error:
            print(f'Löschen fehlgeschlagen ({article_id}): {error}')
    print('Ankündigungs-Abgleich abgeschlossen.')


if __name__ == '__main__':
    main()
