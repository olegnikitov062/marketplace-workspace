"""Узкие действия только над разрешёнными синтетическими UUID стенда."""
import json
import os
import re
import uuid
from pathlib import Path

from django.core.exceptions import PermissionDenied
from django.db import connection, transaction
from django.utils import timezone
from django.views.decorators.debug import sensitive_variables

from account_security import services as security
from account_security.operator import require_operator_process
from accounts.models import AccountContact
from access_control.models import Grant, SyntheticRecord
from access_control.services import revoke_grant
from ownership.models import User, Organization, Cabinet, Membership
from tools.basework_postgresql_rehearsal import marker, PROJECT
from .models import IdentityBinding, ApplicationAccess
from .oidc_configuration import current, unique_object
from .services import revoke_identity, revoke_application

CONFIG = '/run/config/basework_operator.json'
BINDING = '/run/config/basework_identity.json'


def document(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise PermissionDenied()
    raw = path.read_bytes()
    if len(raw) > 8192:
        raise PermissionDenied()
    return json.loads(raw, object_pairs_hook=unique_object)


def roster(value):
    if not isinstance(value, dict) or set(value) != {'project', 'users'} or value['project'] != PROJECT:
        raise PermissionDenied()
    users = value['users']
    if not isinstance(users, list) or not 1 <= len(users) <= 4:
        raise PermissionDenied()
    result = {}
    for user in users:
        if not isinstance(user, dict) or set(user) != {'id', 'username'} or not isinstance(user['id'], str):
            raise PermissionDenied()
        key = str(uuid.UUID(user['id']))
        name = user['username']
        if (key != user['id'] or key in result or not isinstance(name, str)
                or not re.fullmatch(r'basework-uat-[a-z0-9-]{1,48}', name) or name in result.values()):
            raise PermissionDenied()
        result[key] = name
    return result


def guard():
    marker()
    if connection.vendor != 'postgresql' or os.environ.get('BASEWORK_OPERATOR_CONFIG_FILE') != CONFIG:
        raise PermissionDenied()
    require_operator_process()
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_setting('cluster_name'),current_setting('server_version_num')::int,"
                       "rolsuper,rolbypassrls FROM pg_roles WHERE rolname=current_user")
        value = cursor.fetchone()
        if not value or value[0] != PROJECT or not 170000 <= value[1] < 180000 or any(value[2:]):
            raise PermissionDenied()
    return roster(document(CONFIG))


def ids(user_id):
    return {kind: uuid.uuid5(uuid.UUID(user_id), 'basework-uat:' + kind)
            for kind in ('organization', 'cabinet', 'membership', 'record')}


@sensitive_variables()
def password_file(path):
    if not isinstance(path, str) or not re.fullmatch(r'/run/secrets/basework_uat_[a-z0-9_]+', path):
        raise PermissionDenied()
    file = Path(path)
    if file.is_symlink() or not file.is_file():
        raise PermissionDenied()
    raw = file.read_bytes()
    if len(raw) > 512:
        raise PermissionDenied()
    value = raw.decode('ascii').rstrip('\r\n')
    if not 32 <= len(value) <= 128 or not all(33 <= ord(c) <= 126 for c in value):
        raise PermissionDenied()
    return value


def fixture(user_id, name):
    expected = ids(user_id)
    user = User.objects.select_for_update().get(pk=user_id, username=name, archived_at__isnull=True)
    member = Membership.objects.select_for_update().get(pk=expected['membership'], user=user,
        organization_id=expected['organization'], role='observer', state='active', archived_at__isnull=True,
        organization__archived_at__isnull=True)
    cabinet = Cabinet.objects.get(pk=expected['cabinet'], organization_id=expected['organization'],
                                  marketplace='synthetic', archived_at__isnull=True)
    SyntheticRecord.objects.get(pk=expected['record'], organization_id=expected['organization'],
                                cabinet=cabinet, archived_at__isnull=True)
    return user, member, cabinet


@transaction.atomic
@sensitive_variables()
def execute(action, user_id, *, password_path=None):
    allowed = guard()
    user_id = str(uuid.UUID(str(user_id)))
    if user_id not in allowed:
        raise PermissionDenied()
    name = allowed[user_id]
    if action == 'create-user':
        password = password_file(password_path)
        expected = ids(user_id)
        if User.objects.filter(pk=user_id).exists() or User.objects.filter(username=name).exists():
            raise PermissionDenied()
        user = User.objects.create_user(name, password, id=user_id)
        AccountContact.objects.create(user=user, email=name+'@example.invalid', activated_at=timezone.now())
        org = Organization.objects.create(id=expected['organization'], name=name)
        cabinet = Cabinet.objects.create(id=expected['cabinet'], organization=org, name=name, marketplace='synthetic')
        Membership.objects.create(id=expected['membership'], organization=org, user=user, role='observer')
        SyntheticRecord.objects.create(id=expected['record'], organization=org, cabinet=cabinet, value=7)
        security.state_for(user)
        security.event(user, 'basework_stand_user_created')
        return {'user_id': user_id, **{k+'_id': str(v) for k, v in expected.items()}}
    user, member, cabinet = fixture(user_id, name)
    if action == 'bind-identity':
        data = document(BINDING)
        if (not isinstance(data, dict) or set(data) != {'user_id', 'issuer', 'subject'}
                or data['user_id'] != user_id or data['issuer'] != current().issuer
                or not isinstance(data['subject'], str) or not 1 <= len(data['subject']) <= 255
                or any(c.isspace() or ord(c) < 33 for c in data['subject']) or not security.available(user)):
            raise PermissionDenied()
        # Любая история этой пары или пользователя требует отдельного разбора.
        if (IdentityBinding.objects.filter(issuer=data['issuer'], subject=data['subject']).exists()
                or IdentityBinding.objects.filter(user=user, issuer=data['issuer']).exists()):
            raise PermissionDenied()
        binding = IdentityBinding.objects.create(user=user, issuer=data['issuer'], subject=data['subject'])
        security.event(user, 'basework_stand_identity_bound')
        return {'binding_id': str(binding.pk)}
    if action == 'grant-view':
        if not security.available(user) or Grant.objects.filter(membership=member).exists() or ApplicationAccess.objects.filter(user=user, application='marketplace').exists():
            raise PermissionDenied()
        grant = Grant.objects.create(organization_id=member.organization_id, membership=member,
                                     cabinet=cabinet, resource='synthetic_record', action='view')
        access = ApplicationAccess.objects.create(user=user, application='marketplace')
        security.event(user, 'basework_stand_view_granted')
        return {'grant_id': str(grant.pk), 'access_id': str(access.pk)}
    if action == 'revoke-identity':
        # Отзыв нужен и при выключенном OIDC; неоднозначная история отклоняется.
        binding = IdentityBinding.objects.get(user=user)
        revoke_identity(binding.pk)
        return {'binding_id': str(binding.pk)}
    if action == 'revoke-view':
        grant = Grant.objects.select_for_update().get(membership=member, cabinet=cabinet,
                                                      resource='synthetic_record', action='view')
        access = ApplicationAccess.objects.get(user=user, application='marketplace')
        revoke_grant(grant)
        revoke_application(access.pk)
        return {'grant_id': str(grant.pk), 'access_id': str(access.pk)}
    raise PermissionDenied()
