"""Financial projection for the existing synthetic logical table consumers."""
import csv
import io
import re
from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db import connection, DatabaseError, transaction

from data_isolation.context import scope
from .models import SyntheticFinance

FIELDS = ('revenue', 'cost', 'expenses', 'payout')


def grant_for(actor, org, cabinet, action):
    from . import services
    if services.platform_for(actor):
        return None
    try:
        return services.authorize(actor, org, 'synthetic_finance', action, cabinet)
    except PermissionDenied:
        return None


def require(actor, org, cabinet, action, grant_id=None):
    from . import services
    services.authorize(actor, org, 'synthetic_record', action, cabinet)
    if services.platform_for(actor):
        raise PermissionDenied()
    # An export uses its original grant even when a newer overlapping one exists.
    session = services.session_for(actor)
    grants = services.matching(actor, org, 'synthetic_finance', action, cabinet)
    if grant_id is not None:
        grants = grants.filter(pk=grant_id)
    if not grants.exists():
        raise PermissionDenied()
    c = scope.get()
    expected = {'kind': 'record', 'resource': 'synthetic_record', 'action': action,
                'user': str(actor.pk), 'session': str(session.pk),
                'organization': str(org.pk), 'cabinet': str(cabinet.pk)}
    if c != expected:
        raise PermissionDenied()


def amounts(values):
    if set(values) != set(FIELDS):
        raise PermissionDenied()
    result = {}
    for name in FIELDS:
        value = values[name]
        if not isinstance(value, str) or not re.fullmatch(r'[0-9]{1,12}(?:\.[0-9]{1,2})?', value):
            raise PermissionDenied()
        result[name] = Decimal(value)
    return result


def read(actor, org, cabinet, ids, action='view', binding=None):
    require(actor, org, cabinet, action, binding.finance_grant_id if binding else None)
    if len(ids) > 100 or action not in ('view', 'export') or ((action == 'export') != (binding is not None)):
        raise PermissionDenied()
    if binding is not None and (binding.finance_grant_id is None or ids != [binding.record_id]):
        raise PermissionDenied()
    if connection.vendor == 'postgresql':
        try:
            with transaction.atomic(), connection.cursor() as cursor:
                cursor.execute('SELECT * FROM mw_isolation.finance_read(%s::uuid[],%s::uuid)',
                               [ids, binding.permit_id if binding else None])
                rows = cursor.fetchall()
        except DatabaseError:
            raise PermissionDenied() from None
        return {row[0]: dict(zip(FIELDS, row[1:])) for row in rows}
    if connection.vendor != 'sqlite' or not getattr(settings, 'ISOLATION_OFFLINE', False):
        raise PermissionDenied()
    # Explicit offline application tests only. Production has no ORM fallback.
    rows = SyntheticFinance.objects.filter(record_id__in=ids, organization=org, cabinet=cabinet,
                                             record__archived_at__isnull=True).values('record_id', *FIELDS)
    return {row['record_id']: {k: row[k] for k in FIELDS} for row in rows}


def write(actor, org, cabinet, record, values):
    require(actor, org, cabinet, 'change')  # Before parsing or consulting stored values.
    values = amounts(values)
    if connection.vendor == 'postgresql':
        try:
            with transaction.atomic(), connection.cursor() as cursor:
                cursor.execute('SELECT mw_isolation.finance_write(%s,%s,%s,%s,%s)',
                               [record.pk, *(values[f] for f in FIELDS)])
        except DatabaseError:
            raise PermissionDenied() from None
    elif connection.vendor == 'sqlite' and getattr(settings, 'ISOLATION_OFFLINE', False):
        if SyntheticFinance.objects.filter(record=record, organization=org, cabinet=cabinet).update(**values) != 1:
            raise PermissionDenied()
    else:
        raise PermissionDenied()


def output(row):
    if row is None:
        return None
    profit = row['revenue'] - row['cost'] - row['expenses']
    margin = (profit * 100 / row['revenue']).quantize(Decimal('.01'), rounding=ROUND_HALF_UP) if row['revenue'] else None
    return {**{k: format(row[k], '.2f') for k in FIELDS}, 'currency': 'RUB',
            'profit': format(profit, '.2f'), 'margin_percent': str(margin) if margin is not None else None}


def totals(rows):
    return {**output({k: sum((row[k] for row in rows.values()), Decimal(0)) for k in FIELDS}),
            'scope': 'returned_records', 'financial_records': len(rows)}


def csv_bytes(value, finance=None, include_finance=False):
    stream = io.StringIO(newline='')
    writer = csv.writer(stream, lineterminator='\n')
    keys = (*FIELDS, 'currency', 'profit', 'margin_percent') if include_finance else ()
    writer.writerow(('synthetic', 'value', *keys))
    writer.writerow(('example.invalid', value, *((finance or {}).get(k, '') for k in keys)))
    return stream.getvalue().encode('utf-8')
