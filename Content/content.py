"""AION 2 Content: zentrale Verwaltung von Launch und aktiver Season."""
import json
import hashlib
from contextlib import ExitStack
import os
import importlib.util
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import requests
import time

BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / 'content_data.json'
MESSAGE_STATE_FILE = BASE_DIR / 'content_message.json'
WEBHOOK_URL = os.environ.get('CONTENT_WEBHOOK')


def load_json(filename, default=None):
    try:
        return json.loads(filename.read_text(encoding='utf-8'))
    except FileNotFoundError:
        return {} if default is None else default


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f'Modul fehlt: {path}')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_message_state():
    state = load_json(MESSAGE_STATE_FILE)
    if not isinstance(state, dict):
        raise ValueError('Ungültiger Nachrichtenstatus')
    return state


def save_message_state(state):
    MESSAGE_STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def webhook_wait_url():
    if not WEBHOOK_URL:
        raise RuntimeError('GitHub Secret CONTENT_WEBHOOK fehlt.')
    return WEBHOOK_URL + ('&' if '?' in WEBHOOK_URL else '?') + 'wait=true'


def discord_message_url(message_id):
    if not WEBHOOK_URL:
        raise RuntimeError('GitHub Secret CONTENT_WEBHOOK fehlt.')
    return f'{WEBHOOK_URL.split("?", 1)[0]}/messages/{message_id}'


def request_retry(method, url, **kwargs):
    for attempt in range(8):
        response = requests.request(method, url, timeout=30, **kwargs)
        if response.status_code != 429:
            return response
        time.sleep(float(response.json().get('retry_after', 2)) + 0.25)
    return response


def unchanged(message_id, content, files):
    response = request_retry('GET', discord_message_url(message_id))
    if response.status_code == 404:
        return False
    if response.status_code != 200:
        raise RuntimeError(f'Nachrichtenprüfung: HTTP {response.status_code}')
    message = response.json()
    if message.get('content', '') != content:
        return False
    attachments = message.get('attachments', [])
    if len(attachments) != len(files):
        return False
    for attachment, path in zip(attachments, files):
        if attachment.get('size') != Path(path).stat().st_size:
            return False
        # CDN-Datei vergleichen, ohne Webhook-Token weiterzugeben.
        remote = request_retry('GET', attachment['url'])
        if remote.status_code != 200:
            raise RuntimeError(f'Anhangprüfung: HTTP {remote.status_code}')
        if hashlib.sha256(remote.content).digest() != hashlib.sha256(Path(path).read_bytes()).digest():
            return False
    return True


def send_image(method, url, image_file, discord_filename):
    payload = {'content': '', 'allowed_mentions': {'parse': []},
               'attachments': [{'id': 0, 'filename': discord_filename}]}
    with open(image_file, 'rb') as handle:
        return requests.request(method, url, data={'payload_json': json.dumps(payload)},
                                files={'files[0]': (discord_filename, handle, 'image/png')}, timeout=30)


def update_or_create_discord_image(state, state_key, image_file, discord_filename, label):
    message_id = state.get(state_key)
    if message_id and unchanged(message_id, '', [image_file]):
        print(f'{label} unverändert.')
        return False
    if message_id:
        response = send_image('PATCH', discord_message_url(message_id), image_file, discord_filename)
        if response.status_code in (200, 204):
            print(f'{label} aktualisiert: {message_id}')
            return False
        if response.status_code != 404:
            raise RuntimeError(f'{label}: HTTP {response.status_code}: {response.text}')
    response = send_image('POST', webhook_wait_url(), image_file, discord_filename)
    if response.status_code not in (200, 201):
        raise RuntimeError(f'{label}: HTTP {response.status_code}: {response.text}')
    state[state_key] = str(response.json()['id'])
    save_message_state(state)
    print(f'{label} erstellt: {state[state_key]}')
    return True


def should_update(launch, milestone, mode, now, timezone_name):
    target = launch.parse_launch_datetime(milestone['date'], timezone_name)
    remaining = (target - now).total_seconds()
    if mode == 'daily':
        return True
    if remaining <= 0:
        return mode == 'minute' and remaining > -3600
    if mode == 'quarter':
        return 3600 < remaining <= 86400
    return remaining <= 3600


def phase_time(value, tz):
    result = datetime.fromisoformat(value)
    return result.replace(tzinfo=tz) if result.tzinfo is None else result.astimezone(tz)


def update_active_season(data, now, state):
    phases = sorted(data.get('content_phases', []), key=lambda p: phase_time(p['start'], now.tzinfo))
    print('Konfigurierte Seasons: ' + ', '.join(p['key'] for p in phases))
    if not phases:
        raise RuntimeError('Keine Seasons konfiguriert.')
    errors = []
    for phase in phases:
        active = phase_time(phase['start'], now.tzinfo) <= now
        print(f"{phase['key']}: {'vollständige Roadmap' if active else 'nur Banner'}")
        try:
            update_season(phase, now, state, header_only=not active)
        except Exception as exc:
            errors.append(f"{phase['key']}: {exc}")
            print(f"{phase['key']}: FEHLER – {exc}", flush=True)
    if errors:
        raise RuntimeError(' | '.join(errors))


def update_season(phase, now, state, header_only=False):
    folder = BASE_DIR / phase['folder']
    module = load_module(folder / 'season.py', phase['key'])
    components, files = [], []
    for part, payload, paths in module.render(folder, now):
        if header_only and part != 'season_header':
            break
        if payload.get('content'):
            components.append({'type': 10, 'content': payload['content']})
        for path in paths:
            path = Path(path)
            name = f'{len(files)}_{path.name}'
            files.append((name, path))
            components.append({'type': 12, 'items': [{'media': {'url': 'attachment://' + name}}]})
    if not components:
        raise RuntimeError(f"{phase['key']}: keine Inhalte erzeugt")
    if len(files) > 10 or len(components) > 40:
        raise RuntimeError('Discord-Komponentenlimit überschritten.')
    payload = {'flags': 32768, 'components': components, 'allowed_mentions': {'parse': []},
               'attachments': [{'id': i, 'filename': name} for i, (name, _) in enumerate(files)]}
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode())
    for _, path in files:
        digest.update(path.read_bytes())
    fingerprint = digest.hexdigest()
    key = phase['key'] + '_combined_message_id'
    hashkey = phase['key'] + '_combined_hash'
    mid = state.get(key)
    if mid:
        check = request_retry('GET', discord_message_url(mid))
        if check.status_code == 404:
            mid = None
        elif check.status_code != 200:
            raise RuntimeError(f'Nachrichtenprüfung: {check.status_code} {check.text}')
    if not mid or state.get(hashkey) != fingerprint:
        method = 'PATCH' if mid else 'POST'
        url = discord_message_url(mid) if mid else webhook_wait_url()
        url += ('&' if '?' in url else '?') + 'with_components=true'
        print(f"{phase['key']}: {method}, {len(components)} Komponenten, {len(files)} Anhänge", flush=True)
        for attempt in range(8):
            with ExitStack() as stack:
                uploads = {f'files[{i}]': (name, stack.enter_context(path.open('rb')), 'image/png') for i, (name, path) in enumerate(files)}
                response = requests.request(method, url, data={'payload_json': json.dumps(payload)}, files=uploads, timeout=30)
            if response.status_code == 429:
                time.sleep(float(response.json().get('retry_after', 2)) + .25)
                continue
            if method == 'PATCH' and response.status_code in (500, 502, 503, 504) and attempt < 7:
                time.sleep(min(2 ** attempt, 15))
                continue
            break
        if response.status_code not in (200, 201):
            raise RuntimeError(f"{phase['key']}: HTTP {response.status_code}: {response.text}")
        state[key] = str(response.json()['id'])
        state[hashkey] = fingerprint
        save_message_state(state)
        print(f"{phase['key']}: {method} erfolgreich – {state[key]}")
    else:
        print(f"{phase['key']}: unverändert – kein PATCH")
    # Nur bekannte alte Season-Nachrichten entfernen, nachdem Ersatz existiert.
    protected = {str(v) for k,v in state.items() if k in ('early_access_message_id','global_launch_message_id') or k.endswith('_combined_message_id')}
    for old in list(state):
        if not old.endswith('_message_id') or not old.startswith(tuple(phase['key'] + x for x in ('_markdown_', '_png_test_', '_text_month_'))):
            continue
        if str(state[old]) in protected:
            raise RuntimeError('Geschützte Nachricht darf nicht gelöscht werden.')
        response = request_retry('DELETE', discord_message_url(state[old]))
        if response.status_code not in (204,404):
            raise RuntimeError(f'Bereinigung: {response.status_code} {response.text}')
        del state[old]
        save_message_state(state)
        print(f'{old} entfernt.')


def main():
    data = load_json(DATA_FILE)
    if not data:
        raise RuntimeError('content_data.json fehlt oder ist leer.')
    mode = os.environ.get('CONTENT_MODE', 'daily').strip().lower()
    if mode not in ('daily', 'quarter', 'minute'):
        raise ValueError(f'Ungültiger CONTENT_MODE: {mode}')
    timezone_name = data.get('timezone', 'Europe/Berlin')
    now = datetime.now(ZoneInfo(timezone_name))
    launch = load_module(BASE_DIR / 'Launch' / 'launch.py', 'nyerk24_launch')
    state = load_message_state()
    milestones = {m['key']: m for m in launch.build_content_state(data)['milestones']}
    for key in ('early_access', 'global_launch'):
        milestone = milestones[key]
        if should_update(launch, milestone, mode, now, timezone_name):
            path = launch.save_milestone_card(milestone)
            update_or_create_discord_image(state, f'{key}_message_id', path, f'{key}.png', milestone['title'])
    if mode == 'daily':
        update_active_season(data, now, state)


if __name__ == '__main__':
    main()
