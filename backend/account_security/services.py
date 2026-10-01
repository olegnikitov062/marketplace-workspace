import hashlib
import secrets
from contextvars import ContextVar
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import login as django_login, logout as django_logout
from django.contrib.auth.hashers import check_password, make_password
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone
from django.utils.crypto import constant_time_compare
from django.views.decorators.debug import sensitive_variables

from accounts.backends import PersonalAccountBackend
from accounts.limits import allow_attempt, denied
from ownership.models import Membership, User
from ownership.services import membership_role
from .models import (AccountSecurity, AccountSession, Authenticator, ExportPermit, LoginChallenge,
                     RecoveryCode, RecoveryPermit, SecurityEvent, TrustedDevice)

current_session = ContextVar("security_session", default=None)


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def event(user, kind):
    SecurityEvent.objects.create(user=user, kind=kind)


def available(user):
    return (user is not None and PersonalAccountBackend().user_can_authenticate(user)
            and user.has_usable_password())


def state_for(user, lock=False):
    AccountSecurity.objects.get_or_create(user=user)
    query = AccountSecurity.objects.select_for_update() if lock else AccountSecurity.objects
    return query.get(user=user)


def locked_user(user_id):
    user = User.objects.select_for_update().get(pk=user_id)
    if not available(user):
        raise PermissionDenied()
    return user, state_for(user, lock=True)


def required(user):
    return Membership.objects.filter(
        user=user, role=Membership.Role.OWNER, state=Membership.State.ACTIVE,
        archived_at__isnull=True, organization__archived_at__isnull=True,
    ).exists()


def authenticator(user):
    return Authenticator.objects.filter(user=user, confirmed=True, revoked_at__isnull=True).first()


def record_valid(record, user, state, now=None):
    now = now or timezone.now()
    if (not available(user) or record.user_id != user.pk or record.revoked_at
            or record.version != state.version
            or not constant_time_compare(record.credential_hash, user.get_session_auth_hash())
            or record.expires_at <= now
            or record.last_seen + timedelta(seconds=settings.SECURITY_IDLE_SECONDS) <= now):
        return False
    if record.authenticator_id and not Authenticator.objects.filter(
        pk=record.authenticator_id, user=user, confirmed=True, revoked_at__isnull=True,
    ).exists():
        return False
    if record.trusted_device_id and not trusted_valid(record.trusted_device, user, state, now):
        return False
    if record.level == AccountSession.Level.FULL:
        if state.recovery_required:
            return False
        if (required(user) or authenticator(user)) and record.authenticator_id is None:
            return False
    return True


def assert_actor_session(user):
    """Recheck after the E2-05 service acquired its user row lock."""
    session_id = current_session.get()
    if session_id is None:
        return  # Direct trusted service calls have no HTTP session context.
    record = AccountSession.objects.filter(pk=session_id, user=user).first()
    if (record is None or record.level != AccountSession.Level.FULL
            or not record_valid(record, user, state_for(user))):
        raise PermissionDenied()


def trusted_valid(device, user, state, now=None):
    now = now or timezone.now()
    return (device is not None and device.user_id == user.pk and device.revoked_at is None
            and device.version == state.version and device.expires_at > now
            and constant_time_compare(device.credential_hash, user.get_session_auth_hash())
            and Authenticator.objects.filter(pk=device.authenticator_id, user=user,
                                              confirmed=True, revoked_at__isnull=True).exists())


@sensitive_variables()
def remembered(request, user, state):
    raw = request.COOKIES.get(settings.SECURITY_TRUST_COOKIE, "")
    if len(raw) != 43:
        return None
    device = TrustedDevice.objects.filter(token_hash=digest(raw), user=user).first()
    return device if trusted_valid(device, user, state) else None


def revoke_all_locked(user, state, kind):
    """Caller holds user -> AccountSecurity locks, including password/block paths."""
    now = timezone.now()
    state.version += 1
    state.save(update_fields=["version"])
    AccountSession.objects.filter(user=user, revoked_at__isnull=True).update(revoked_at=now)
    TrustedDevice.objects.filter(user=user, revoked_at__isnull=True).update(revoked_at=now)
    ExportPermit.objects.filter(user=user, revoked_at__isnull=True).update(revoked_at=now)
    event(user, kind)


@transaction.atomic
def credentials_changed(user, kind):
    # Called under the pre-existing E2-05 User lock; blocked users are intentional.
    state = state_for(user, lock=True)
    revoke_all_locked(user, state, kind)


@sensitive_variables()
def register_session(request, user, state, level, device=None, trust=None, factor=False):
    old = AccountSession.objects.filter(session_hash=digest(request.session.session_key or ""),
                                        revoked_at__isnull=True)
    old.update(revoked_at=timezone.now())
    django_login(request, user, backend="accounts.backends.PersonalAccountBackend")
    request.session.cycle_key()
    lifetime = settings.SESSION_COOKIE_AGE if level == "full" else settings.SECURITY_CHALLENGE_SECONDS
    request.session.set_expiry(lifetime)
    request.session.save()
    now = timezone.now()
    record = AccountSession.objects.create(
        user=user, session_hash=digest(request.session.session_key),
        credential_hash=user.get_session_auth_hash(), version=state.version, level=level,
        authenticator=device, trusted_device=trust, created_at=now, last_seen=now,
        expires_at=now + timedelta(seconds=lifetime), password_confirmed_at=now,
        factor_confirmed_at=now if factor else None,
    )
    request.security_session = record
    return record


@sensitive_variables()
@transaction.atomic
def complete_login(request, user_id, challenge_id, device_id=None, remember=False):
    user, state = locked_user(user_id)
    challenge = LoginChallenge.objects.select_for_update().filter(pk=challenge_id, user=user,
        used_at__isnull=True, expires_at__gt=timezone.now()).first()
    if (challenge is None or state.version != challenge.version
            or not constant_time_compare(challenge.credential_hash, user.get_session_auth_hash())):
        raise PermissionDenied()
    device = Authenticator.objects.filter(pk=device_id, user=user, confirmed=True,
                                          revoked_at__isnull=True).first() if device_id else None
    trust = None if device else remembered(request, user, state)
    existing = authenticator(user)
    if state.recovery_required:
        raise PermissionDenied()  # Operator/recovery-code flow only.
    if existing and device is None and trust is None:
        raise PermissionDenied()
    challenge.used_at = timezone.now()
    challenge.save(update_fields=["used_at"])
    level = "enroll" if required(user) and existing is None else "full"
    used_device = device or (trust.authenticator if trust else None)
    register_session(request, user, state, level, used_device, trust, bool(device))
    raw_trust = None
    if remember and device:
        raw_trust = secrets.token_urlsafe(32)
        TrustedDevice.objects.create(user=user, authenticator=device,
            token_hash=digest(raw_trust), credential_hash=user.get_session_auth_hash(),
            version=state.version, expires_at=timezone.now() + timedelta(seconds=settings.SECURITY_TRUST_SECONDS))
    event(user, "login_" + level)
    return level, raw_trust


@transaction.atomic
def logout(request, all_sessions=False, selected=None):
    if not request.user.is_authenticated:
        django_logout(request)
        return
    user, state = locked_user(request.user.pk)
    if all_sessions:
        revoke_all_locked(user, state, "logout_all")
    else:
        record = AccountSession.objects.select_for_update().get(
            pk=selected or request.security_session.pk, user=user)
        now = timezone.now()
        AccountSession.objects.filter(pk=record.pk, revoked_at__isnull=True).update(revoked_at=now)
        ExportPermit.objects.filter(session=record, revoked_at__isnull=True).update(revoked_at=now)
        event(user, "session_revoked")
    if all_sessions or selected is None or str(selected) == str(request.security_session.pk):
        django_logout(request)


def fresh(record, factor=True):
    minimum = timezone.now() - timedelta(seconds=settings.SECURITY_REAUTH_SECONDS)
    return (record.password_confirmed_at is not None and record.password_confirmed_at > minimum
            and (not factor or record.factor_confirmed_at is not None and record.factor_confirmed_at > minimum))


@sensitive_variables()
def verify_factor(user_id, token, device_id=None, enrollment=False, enrollment_hash=None):
    # Preserve upstream failure counters by returning False, never raising inside atomic.
    with transaction.atomic():
        user, state = locked_user(user_id)
        query = Authenticator.objects.select_for_update().filter(user=user, revoked_at__isnull=True)
        if enrollment:
            if device_id is None or not enrollment_hash:
                return None
            query = query.filter(enrollment_hash=enrollment_hash)
        if device_id is not None:
            query = query.filter(pk=device_id)
        device = query.filter(confirmed=not enrollment).first()
        if device is None or enrollment and (device.expires_at <= timezone.now()
                                              or device.enrollment_version != state.version):
            return None
        return device if device.verify_token(token) else None


@sensitive_variables()
def reauthenticate(request, password, token):
    if not allow_attempt("mfa_reauth", request.META.get("REMOTE_ADDR", ""), str(request.user.pk)):
        return False
    with transaction.atomic():
        user, state = locked_user(request.user.pk)
        record = AccountSession.objects.select_for_update().get(pk=request.security_session.pk)
        if not record_valid(record, user, state) or not user.check_password(password):
            return False
        device = authenticator(user)
        if device and verify_factor(user.pk, token, device.pk) is None:
            return False
        record.password_confirmed_at = timezone.now()
        record.factor_confirmed_at = timezone.now() if device else None
        record.save(update_fields=["password_confirmed_at", "factor_confirmed_at"])
        request.security_session = record
        return True


@sensitive_variables()
@transaction.atomic
def begin_enrollment(request):
    user, state = locked_user(request.user.pk)
    record = AccountSession.objects.select_for_update().get(pk=request.security_session.pk)
    if not record_valid(record, user, state) or not fresh(record, factor=record.level == "full" and authenticator(user) is not None):
        raise PermissionDenied()
    # A new setup invalidates prior unconfirmed setups in this session only.
    Authenticator.objects.filter(user=user, confirmed=False, revoked_at__isnull=True,
                                 enrollment_hash=record.session_hash).update(revoked_at=timezone.now())
    device = Authenticator.objects.create(user=user, confirmed=False, name="default",
        enrollment_hash=record.session_hash, enrollment_version=state.version,
        expires_at=timezone.now() + timedelta(seconds=settings.SECURITY_CHALLENGE_SECONDS))
    request.session["security_setup_id"] = device.pk
    return device


@sensitive_variables()
@transaction.atomic
def finish_enrollment(request, device_id):
    user, state = locked_user(request.user.pk)
    record = AccountSession.objects.select_for_update().get(pk=request.security_session.pk)
    if not record_valid(record, user, state):
        raise PermissionDenied()
    device = Authenticator.objects.select_for_update().get(pk=device_id, user=user, confirmed=False,
        revoked_at__isnull=True, enrollment_hash=record.session_hash, enrollment_version=state.version)
    if device.last_t < 0 or device.expires_at <= timezone.now() or request.session.get("security_setup_verified") != device.pk:
        raise PermissionDenied()
    now = timezone.now()
    Authenticator.objects.filter(user=user, confirmed=True, revoked_at__isnull=True).update(revoked_at=now, confirmed=False)
    device.confirmed = True
    device.expires_at = None
    device.save(update_fields=["confirmed", "expires_at"])
    state.recovery_required = False
    state.save(update_fields=["recovery_required"])
    revoke_all_locked(user, state, "mfa_enrolled")
    RecoveryCode.objects.filter(user=user, used_at__isnull=True).update(used_at=now)
    codes = [secrets.token_urlsafe(24) for _ in range(settings.SECURITY_RECOVERY_CODE_COUNT)]
    RecoveryCode.objects.bulk_create([RecoveryCode(user=user, verifier=make_password(code)) for code in codes])
    # No authenticated session remains after factor replacement/enrollment.
    django_logout(request)
    return codes


@sensitive_variables()
def recover_with_code(request, username, password, code):
    if not allow_attempt("mfa_recovery", request.META.get("REMOTE_ADDR", ""), username):
        return False
    with transaction.atomic():
        user = User.objects.select_for_update().filter(username=User.normalize_username(username)).first()
        if not available(user) or not user.check_password(password):
            return False
        state = state_for(user, lock=True)
        match = None
        for candidate in RecoveryCode.objects.select_for_update().filter(user=user, used_at__isnull=True):
            if check_password(code, candidate.verifier):
                match = candidate
        if match is None:
            return False
        match.used_at = timezone.now()
        match.save(update_fields=["used_at"])
        state.recovery_required = True
        state.save(update_fields=["recovery_required"])
        revoke_all_locked(user, state, "code_recovery")
        register_session(request, user, state, "recover")
        return True


@sensitive_variables()
@transaction.atomic
def issue_operator_recovery(user_id):
    """Trusted CLI only, never callable through a web URL or with web INSERT ACL."""
    user, state = locked_user(user_id)
    if not required(user):
        raise PermissionDenied()
    state.recovery_required = True
    state.save(update_fields=["recovery_required"])
    revoke_all_locked(user, state, "operator_recovery_issued")
    token = secrets.token_urlsafe(32)
    RecoveryPermit.objects.create(user=user, token_hash=digest(token), version=state.version,
        expires_at=timezone.now() + timedelta(seconds=settings.SECURITY_CHALLENGE_SECONDS))
    return token


@sensitive_variables()
def consume_operator_recovery(request, username, password, token):
    if not allow_attempt("operator_recovery", request.META.get("REMOTE_ADDR", ""), username):
        return False
    with transaction.atomic():
        user = User.objects.select_for_update().filter(username=User.normalize_username(username)).first()
        if not available(user) or not user.check_password(password) or not required(user):
            return False
        state = state_for(user, lock=True)
        permit = RecoveryPermit.objects.select_for_update().filter(user=user, token_hash=digest(token),
            version=state.version, used_at__isnull=True, expires_at__gt=timezone.now()).first()
        if permit is None or not state.recovery_required:
            return False
        permit.used_at = timezone.now()
        permit.save(update_fields=["used_at"])
        register_session(request, user, state, "recover")
        event(user, "operator_recovery_consumed")
        return True


@transaction.atomic
def disable(request):
    user, state = locked_user(request.user.pk)
    record = AccountSession.objects.select_for_update().get(pk=request.security_session.pk)
    if required(user) or not record_valid(record, user, state) or not fresh(record):
        raise PermissionDenied()
    now = timezone.now()
    Authenticator.objects.filter(user=user, revoked_at__isnull=True).update(revoked_at=now, confirmed=False)
    RecoveryCode.objects.filter(user=user, used_at__isnull=True).update(used_at=now)
    revoke_all_locked(user, state, "mfa_disabled")
    django_logout(request)


@transaction.atomic
def issue_export_probe(user, organization, session):
    if not settings.SECURITY_DOWNLOAD_PROBE:
        raise PermissionDenied()
    user, state = locked_user(user.pk)
    session = AccountSession.objects.get(pk=session.pk, user=user)
    if (session.level != "full" or not record_valid(session, user, state)
            or membership_role(user, organization) is None):
        raise PermissionDenied()
    return ExportPermit.objects.create(user=user, organization=organization, session=session,
        expires_at=timezone.now() + timedelta(minutes=5))


@transaction.atomic
def read_export_probe(request, permit_id):
    if not settings.SECURITY_DOWNLOAD_PROBE:
        raise PermissionDenied()
    user, state = locked_user(request.user.pk)
    record = AccountSession.objects.get(pk=request.security_session.pk, user=user)
    permit = ExportPermit.objects.select_related("organization").filter(pk=permit_id, user=user,
        session=record, revoked_at__isnull=True, expires_at__gt=timezone.now()).first()
    if (permit is None or record.level != "full" or not record_valid(record, user, state)
            or membership_role(user, permit.organization) is None):
        raise PermissionDenied()
    return b"synthetic,value\nexample.invalid,1\n"


@transaction.atomic
def quarantine_restored_access():
    """Explicit restore-only operation, never run at ordinary startup.

    A historical DB cannot know revocations made after its snapshot. Keep every
    restored account in recovery until the operator reconciles current authority.
    No membership is re-granted or user unblocked by this operation.
    """
    now = timezone.now()
    for user in User.objects.select_for_update().order_by("pk"):
        state = state_for(user, lock=True)
        state.recovery_required = True
        state.save(update_fields=["recovery_required"])
        revoke_all_locked(user, state, "restored_access_quarantined")
        Authenticator.objects.filter(user=user, revoked_at__isnull=True).update(revoked_at=now, confirmed=False)
        RecoveryCode.objects.filter(user=user, used_at__isnull=True).update(used_at=now)
