"""Чтение прежнего FAQ API без ключа редактора, записи и постоянного кэша."""
import json
from http.client import HTTPException
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

from django.conf import settings

MAX_BYTES = 4 * 1024 * 1024


class SourceUnavailable(Exception):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise SourceUnavailable()


def source_url():
    value = getattr(settings, 'BASEWORK_FAQ_URL', '')
    try:
        url = urlsplit(value)
        if (not isinstance(value, str) or any(c.isspace() for c in value)
                or url.scheme not in ('http', 'https') or not url.hostname
                or url.username is not None or url.password is not None
                or url.path != '/api/items' or url.query or url.fragment):
            raise ValueError()
        url.port
    except (ValueError, TypeError):
        raise SourceUnavailable() from None
    return value


def configured():
    try:
        source_url()
        return True
    except SourceUnavailable:
        return False


def text(value):
    if not isinstance(value, str):
        raise ValueError()
    return value.strip()


def parse_document(raw):
    """Белый список полей: служебные поля источника не уходят в браузер."""
    if len(raw) > MAX_BYTES:
        raise ValueError()
    doc = json.loads(raw)
    if not isinstance(doc, dict) or type(doc.get('version')) is not int or doc['version'] < 0:
        raise ValueError()
    if not isinstance(doc.get('updatedAt', ''), str):
        raise ValueError()
    people, items = doc.get('people', []), doc.get('items')
    if not isinstance(people, list) or len(people) > 1000 or not isinstance(items, list) or len(items) > 5000:
        raise ValueError()
    normalized_people, normalized_items, names, ids = [], [], set(), set()
    for person in people:
        if isinstance(person, str):
            person = {'name': person}
        if not isinstance(person, dict):
            raise ValueError()
        name, role = text(person.get('name', '')), text(person.get('role', ''))
        if not name or name in names:
            raise ValueError()
        names.add(name)
        normalized_people.append({'name': name, 'role': role})
    for item in items:
        if not isinstance(item, dict):
            raise ValueError()
        item_id, cat, question = (text(item.get(key, '')) for key in ('id', 'cat', 'q'))
        if not item_id or not cat or not question or item_id in ids:
            raise ValueError()
        ids.add(item_id)
        contacts = item.get('contacts', [])
        if not isinstance(contacts, list) or len(contacts) > 1000:
            raise ValueError()
        normalized_contacts = []
        for contact in contacts:
            if isinstance(contact, dict):
                contact = [contact.get('name', ''), contact.get('note', '')]
            if not isinstance(contact, list) or not 1 <= len(contact) <= 2:
                raise ValueError()
            name, note = text(contact[0]), text(contact[1]) if len(contact) == 2 else ''
            if not name and not note:
                continue
            if name not in names:
                raise ValueError()
            normalized_contacts.append([name, note])
        normalized_items.append({'id': item_id, 'cat': cat, 'q': question, 'contacts': normalized_contacts})
    return {'version': doc['version'], 'updatedAt': doc.get('updatedAt', ''),
            'people': normalized_people, 'items': normalized_items}


def read_source():
    request = Request(source_url(), headers={'Accept': 'application/json'}, method='GET')
    try:
        # Ни cookie пользователя, ни ключ редактора, ни системный proxy не передаются.
        with build_opener(ProxyHandler({}), NoRedirect()).open(request, timeout=5) as response:
            if response.status != 200 or response.headers.get_content_type() != 'application/json':
                raise SourceUnavailable()
            return parse_document(response.read(MAX_BYTES + 1))
    except (HTTPError, URLError, HTTPException, OSError, ValueError, TypeError, RecursionError):
        raise SourceUnavailable() from None


def search(doc, query='', category=''):
    normalize = lambda value: value.casefold().replace('ё', 'е')
    words = normalize(query).split()
    roles = {p['name']: p['role'] for p in doc['people']}
    def matches(item):
        haystack = normalize(' '.join([item['q'], item['cat'],
            *[part for name, note in item['contacts'] for part in (name, note, roles[name])]]))
        return (not category or item['cat'] == category) and all(word in haystack for word in words)
    return {**doc, 'items': [item for item in doc['items'] if matches(item)],
            'categories': list(dict.fromkeys(item['cat'] for item in doc['items'])),
            'total': len(doc['items'])}
