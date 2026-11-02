"""Узкий адаптер переговорок. Брони и привязки пользователей остаются в источнике."""
import hashlib
import hmac
import json
import re
import time
import uuid
from datetime import datetime
from http.client import HTTPException
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

from django.conf import settings

MAX_BYTES = 2 * 1024 * 1024


class SourceUnavailable(Exception):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise SourceUnavailable()


def configuration():
    value = getattr(settings, 'BASEWORK_ROOMS_URL', '')
    try:
        url = urlsplit(value)
        if (url.scheme not in ('http', 'https') or not url.hostname or url.username or url.password
                or url.path != '/api/basework' or url.query or url.fragment or any(c.isspace() for c in value)
                or (url.scheme == 'http' and url.hostname not in ('127.0.0.1', 'localhost', '::1'))):
            raise ValueError()
        url.port
        key = Path(getattr(settings, 'BASEWORK_ROOMS_KEY_FILE', '')).read_bytes()
        if len(key) != 32:
            raise ValueError()
        return value, key
    except (ValueError, TypeError, OSError):
        raise SourceUnavailable() from None


def configured():
    try:
        configuration()
        return True
    except SourceUnavailable:
        return False


def timestamp(value):
    if not isinstance(value, str) or len(value) > 40:
        raise ValueError()
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.utcoffset() is None:
        raise ValueError()
    return parsed


def conflict_details(value):
    # Только публичные поля брони; owner, технические ошибки и прочие поля не выдаём.
    if not isinstance(value, dict):
        return {}
    conflicts = value.get('conflicts')
    values = [value['conflict']] if 'conflict' in value else [item.get('with') for item in conflicts[:3] if isinstance(item, dict)] if isinstance(conflicts, list) else []
    result = []
    for item in values:
        if not isinstance(item, dict) or any(not isinstance(item.get(k), str) or len(item[k]) > 200 for k in ('roomId', 'title')):
            raise ValueError()
        if timestamp(item['end']) <= timestamp(item['start']):
            raise ValueError()
        result.append({k: item[k] for k in ('roomId', 'title', 'start', 'end')})
    return {'conflicts': result} if result else {}


def event(value):
    if not isinstance(value, dict):
        raise ValueError()
    fields = ('id', 'roomId', 'title', 'start', 'end', 'createdBy', 'updatedBy', 'revision')
    if any(not isinstance(value.get(k), str) for k in fields) or any(type(value.get(k)) is not bool for k in ('mine', 'canEdit')):
        raise ValueError()
    if not re.fullmatch('[a-f0-9]{32}', value['id']) or not re.fullmatch('[a-f0-9]{64}', value['revision']):
        raise ValueError()
    result = {k: value[k] for k in (*fields, 'mine', 'canEdit')}
    if value.get('updatedAt'):
        timestamp(value['updatedAt'])
        result['updatedAt'] = value['updatedAt']
    if value.get('seriesId'):
        if not isinstance(value['seriesId'], str) or not re.fullmatch('[a-f0-9]{32}', value['seriesId']):
            raise ValueError()
        result['seriesId'] = value['seriesId']
    return result


def document(value):
    if not isinstance(value, dict) or not isinstance(value.get('events'), list) or not isinstance(value.get('rooms'), list):
        raise ValueError()
    if len(value['events']) > 10000 or not 1 <= len(value['rooms']) <= 100:
        raise ValueError()
    rooms = []
    for room in value['rooms']:
        if not isinstance(room, dict) or not all(isinstance(room.get(k), str) and room[k] for k in ('id', 'name')):
            raise ValueError()
        rooms.append({k: room[k] for k in ('id', 'name')})
        if isinstance(room.get('color'), str) and re.fullmatch(r'#[a-fA-F0-9]{6}', room['color']):
            rooms[-1]['color'] = room['color']
    events = [event(ev) for ev in value['events']]
    if len({ev['id'] for ev in events}) != len(events) or any(ev['roomId'] not in {r['id'] for r in rooms} for ev in events):
        raise ValueError()
    user = value.get('user')
    if not isinstance(user, dict) or not isinstance(user.get('name'), str) or user.get('role') not in ('admin', 'employee'):
        raise ValueError()
    policy = {'timeZone': 'Europe/Moscow', 'weekdays': [1, 2, 3, 4, 5], 'start': '08:00', 'end': '19:00'}
    if value.get('policy') != policy:
        raise ValueError()
    return {'events': events, 'rooms': rooms, 'user': {k: user[k] for k in ('name', 'role')}, 'policy': policy,
            'canWrite': bool(getattr(settings, 'BASEWORK_ROOMS_WRITES', False))}


def exchange(actor, method, path, body, operation):
    url, key = configuration()
    raw = json.dumps({'actor': str(actor), 'method': method, 'path': path, 'body': body,
                      'operation': str(operation), 'sentAt': int(time.time())}, separators=(',', ':')).encode()
    if len(raw) > 500_000:
        return 400, {'status': 'invalid_request'}
    request = Request(url, data=raw, method='POST', headers={'Content-Type': 'application/json',
        'Accept': 'application/json', 'X-Basework-Signature': hmac.new(key, raw, hashlib.sha256).hexdigest()})
    started = time.monotonic()
    try:
        try:
            response = build_opener(ProxyHandler({}), NoRedirect()).open(request, timeout=3)
        except HTTPError as error:
            response = error
        with response:
            if response.headers.get_content_type() != 'application/json':
                raise ValueError()
            chunks, size = [], 0
            while True:
                chunk = response.read1(min(65536, MAX_BYTES + 1 - size))
                size += len(chunk)
                if size > MAX_BYTES or time.monotonic() - started > 5:
                    raise ValueError()
                if not chunk:
                    break
                chunks.append(chunk)
            value = json.loads(b''.join(chunks))
            status = response.status
        if status == 200 and method == 'GET':
            return status, document(value)
        if status in (200, 201) and method != 'GET' and isinstance(value, dict):
            if method == 'POST' and status == 201 and isinstance(value.get('created'), list) and type(value.get('skipped')) is int:
                return 201, {'created': [event(ev) for ev in value['created']], 'skipped': value['skipped']}
            field = 'updated' if method == 'PUT' else 'deleted'
            if type(value.get(field)) is int and value[field] >= 0:
                return 200, {field: value[field]}
            raise ValueError()
        if status in (400, 403, 404, 409):
            # Технические подробности и произвольные поля источника наружу не выдаются.
            code = value.get('status') if isinstance(value, dict) else None
            if code not in ('identity_unbound', 'native_access_denied', 'stale', 'operation_conflict'):
                code = {400: 'invalid_request', 403: 'denied', 404: 'not_found', 409: 'conflict'}[status]
            details = conflict_details(value) if status == 409 and code == 'conflict' else {}
            return status, {'status': code, **details}
        raise ValueError()
    except (HTTPError, URLError, HTTPException, OSError, ValueError, TypeError, KeyError, RecursionError, SourceUnavailable):
        raise SourceUnavailable() from None


def operation_id(value):
    try:
        return str(uuid.UUID(value)) if str(uuid.UUID(value)) == value else None
    except (ValueError, TypeError, AttributeError):
        return None
