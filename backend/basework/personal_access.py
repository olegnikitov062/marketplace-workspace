"""Личный вход без почтовых заглушек; код выдаётся только отдельным оператором."""
import json
import os
import re
import uuid
from pathlib import Path

from django.core import signing
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import connection, transaction
from django.utils.crypto import constant_time_compare
from django.utils.translation import override
from django.views.decorators.debug import sensitive_variables

from account_security import services as security
from account_security.models import SecurityEvent
from account_security.operator import require_operator_process, write_private_new
from accounts.models import AccountContact
from ownership.models import User
from .models import Administrator, ApplicationAccess
from .services import revoke_application
from .password_forms import PersonalSetPasswordForm

CONFIG = '/run/config/basework_personal.json'
OUTPUT = Path('/run/basework-personal-output')
SALT = 'basework.personal-access.v1'
LIFETIME = 30 * 60
CREATED = 'basework_personal_created'
APPLICATIONS = frozenset({'faq', 'rooms'})


def roster(value):
    if not isinstance(value, dict) or set(value) != {'purpose', 'users'} or value['purpose'] != 'basework-personal-pilot-v1':
        raise PermissionDenied()
    users = value['users']
    if not isinstance(users, list) or not 1 <= len(users) <= 20:
        raise PermissionDenied()
    result, names = {}, set()
    for entry in users:
        if not isinstance(entry, dict) or set(entry) != {'id', 'username', 'applications'}:
            raise PermissionDenied()
        key, name, apps = entry['id'], entry['username'], entry['applications']
        if (not isinstance(key, str) or str(uuid.UUID(key)) != key or key in result
                or not isinstance(name, str) or not re.fullmatch(r'[a-z][a-z0-9._-]{2,63}', name)
                or name in names or name.startswith('basework-uat-') or 'synthetic' in name
                or not isinstance(apps, list) or not apps or len(apps) != len(set(apps))
                or not set(apps) <= APPLICATIONS):
            raise PermissionDenied()
        result[key] = entry
        names.add(name)
    return result


def guard():
    require_operator_process()
    if connection.vendor != 'postgresql' or os.environ.get('BASEWORK_PERSONAL_CONFIG_FILE') != CONFIG:
        raise PermissionDenied()
    with connection.cursor() as cursor:
        cursor.execute("SELECT rolsuper,rolbypassrls FROM pg_roles WHERE rolname=current_user")
        if cursor.fetchone() != (False, False):
            raise PermissionDenied()
    path = Path(CONFIG)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 16_384:
        raise PermissionDenied()
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise PermissionDenied()
            result[key] = value
        return result
    return roster(json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=unique))


def personal_user(user):
    if (not user.is_active or user.archived_at or AccountContact.objects.filter(user=user).exists()
            or not SecurityEvent.objects.filter(user=user, kind=CREATED).exists()):
        raise PermissionDenied()
    return user


@sensitive_variables()
def access_code(user, state):
    return signing.dumps({'user': str(user.pk), 'version': state.version,
                          'credential': user.get_session_auth_hash()}, salt=SALT, compress=True)


@transaction.atomic
@sensitive_variables()
def use_code(code, password1, password2):
    try:
        if not isinstance(code, str) or not 1 <= len(code) <= 512:
            raise PermissionDenied()
        value = signing.loads(code, salt=SALT, max_age=LIFETIME)
        if not isinstance(value, dict) or set(value) != {'user', 'version', 'credential'}:
            raise PermissionDenied()
        user = personal_user(User.objects.select_for_update().get(pk=uuid.UUID(value['user'])))
        state = security.state_for(user, lock=True)
        # Выдача кода отключает прежний пароль; новый пароль и версия гасят код навсегда.
        if (user.has_usable_password() or state.recovery_required or value['version'] != state.version
                or not isinstance(value['credential'], str)
                or not constant_time_compare(value['credential'], user.get_session_auth_hash())):
            raise PermissionDenied()
    except (signing.BadSignature, User.DoesNotExist, ValueError, TypeError, KeyError):
        raise PermissionDenied() from None
    with override('ru'):
        form = PersonalSetPasswordForm(user, {'new_password1': password1, 'new_password2': password2})
        if not form.is_valid():
            raise ValidationError(form.errors.as_data())
    form.save(commit=False)
    user.save(update_fields=['password'])
    security.credentials_changed(user, 'basework_personal_password_set')
    return user.username


@sensitive_variables()
def issue_code(user, state):
    user.set_unusable_password()
    user.save(update_fields=['password'])
    security.revoke_all_locked(user, state, 'basework_personal_code_issued')
    return access_code(user, state)


@transaction.atomic
@sensitive_variables()
def execute(action, user_id, *, output=None):
    allowed = guard()
    key = str(uuid.UUID(str(user_id)))
    if key not in allowed or action not in {'create', 'issue-access', 'grant', 'revoke', 'grant-admin', 'revoke-admin'}:
        raise PermissionDenied()
    entry = allowed[key]
    path = None
    if action in {'create', 'issue-access'}:
        path = Path(output or '')
        if (not path.is_absolute() or path.parent.resolve() != OUTPUT or path.is_symlink()
                or path.exists() or not re.fullmatch(r'[a-zA-Z0-9_-]+\.txt', path.name)):
            raise PermissionDenied()
    elif output is not None:
        raise PermissionDenied()
    if action == 'create':
        if User.objects.filter(pk=key).exists() or User.objects.filter(username=entry['username']).exists():
            raise PermissionDenied()
        user = User.objects.create_user(entry['username'], id=key)
        security.event(user, CREATED)
    else:
        user = personal_user(User.objects.select_for_update().get(pk=key, username=entry['username']))
    state = security.state_for(user, lock=True)
    if state.recovery_required:
        raise PermissionDenied()
    if path is not None:
        write_private_new(path, (issue_code(user, state) + '\n').encode('utf-8'))
    elif action == 'grant-admin':
        from access_control.operator import assign_platform
        from access_control.models import PlatformRoleAssignment
        if not PlatformRoleAssignment.objects.filter(user=user, revoked_at__isnull=True).exists():
            assign_platform(user.pk)
            state.refresh_from_db()
        if not Administrator.objects.filter(user=user, revoked_at__isnull=True).exists():
            Administrator.objects.create(user=user)
            security.revoke_all_locked(user, state, 'basework_admin_assigned')
    elif action == 'revoke-admin':
        from django.utils import timezone
        Administrator.objects.filter(user=user, revoked_at__isnull=True).update(revoked_at=timezone.now())
        security.revoke_all_locked(user, state, 'basework_admin_revoked')
    elif action == 'grant':
        for application in entry['applications']:
            if not ApplicationAccess.objects.filter(user=user, application=application, revoked_at__isnull=True).exists():
                ApplicationAccess.objects.create(user=user, application=application)
        security.event(user, 'basework_personal_access_granted')
    else:
        for access in ApplicationAccess.objects.filter(user=user, application__in=entry['applications'], revoked_at__isnull=True):
            revoke_application(access.pk)
    return {'user_id': key, 'username': user.username, 'operation': action, 'code_lifetime_seconds': LIFETIME if path else None}
