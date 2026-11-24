"""AION 2 Content: zentrale Verwaltung von Launch und aktiver Season."""
import json
from contextlib import ExitStack
import os
import importlib.util
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import requests

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


def send_image(method, url, image_file, discord_filename):
    payload = {'content': '', 'allowed_mentions': {'parse': []},
               'attachments': [{'id': 0, 'filename': discord_filename}]}
    with open(image_file, 'rb') as handle:
        return requests.request(method, url, data={'payload_json': json.dumps(payload)},
                                files={'files[0]': (discord_filename, handle, 'image/png')}, timeout=30)


def update_or_create_discord_image(state, state_key, image_file, discord_filename, label):
    message_id = state.get(state_key)
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
    active = [p for p in data.get('content_phases', [])
              if phase_time(p['start'], now.tzinfo) <= now
              and (not p.get('end') or now < phase_time(p['end'], now.tzinfo))]
    if len(active) > 1:
        raise RuntimeError('Mehrere aktive Seasons konfiguriert.')
    if not active:
        print('Keine aktive Season konfiguriert.')
        return
    phase = active[0]
    folder = BASE_DIR / phase['folder']
    module = load_module(folder / 'season.py', phase['key'])
    current_keys = set()
    for month_key, payload, files in module.render(folder):
        key = f"{phase['key']}_text_{month_key}_message_id"
        current_keys.add(key)
        message_id = state.get(key)
        payload['attachments'] = [{'id': i, 'filename': path.name} for i, path in enumerate(files)]
        def send(method, url):
            with ExitStack() as stack:
                uploads = {f'files[{i}]': (path.name, stack.enter_context(path.open('rb')), 'image/png') for i, path in enumerate(files)}
                return requests.request(method, url, data={'payload_json': json.dumps(payload)}, files=uploads, timeout=30)
        response = send('PATCH', discord_message_url(message_id)) if message_id else None
        if response is None or response.status_code == 404:
            response = send('POST', webhook_wait_url())
        if response.status_code not in (200, 201):
            raise RuntimeError(f'{month_key}: HTTP {response.status_code}: {response.text}')
        state[key] = str(response.json()['id'])
        save_message_state(state)
        print(f'{month_key} aktualisiert: {state[key]}')
    # Erst nach erfolgreicher Veröffentlichung alle PNG-Testnachrichten dieser Season entfernen.
    protected = {str(state.get('early_access_message_id')), str(state.get('global_launch_message_id'))}
    for key in list(state):
        if not key.endswith('_message_id') or not (key.startswith(f"{phase['key']}_png_test_") or (key.startswith(f"{phase['key']}_text_month_") and key not in current_keys)):
            continue
        if str(state[key]) in protected:
            raise RuntimeError('Launch-Nachricht darf nicht gelöscht werden.')
        response = requests.delete(discord_message_url(state[key]), timeout=30)
        if response.status_code not in (204, 404):
            raise RuntimeError(f'PNG-Bereinigung: HTTP {response.status_code}: {response.text}')
        del state[key]
        save_message_state(state)
        print(f'{key} entfernt.')


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
