from datetime import timedelta

from django.conf import settings
from django.contrib.auth import logout
from django.http import JsonResponse
from django.utils import timezone
from django.utils.cache import patch_cache_control

from .models import AccountSession
from .services import current_session, digest, record_valid, state_for


class SessionGate:
    """Every authenticated request must carry a current server-side registry row."""
    PARTIAL = frozenset({"/auth/mfa/setup/", "/auth/mfa/qr/", "/auth/logout", "/auth/csrf"})

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.security_session = None
        if request.user.is_authenticated:
            record = AccountSession.objects.filter(user=request.user,
                session_hash=digest(request.session.session_key or "")).first()
            if record is None or not record_valid(record, request.user, state_for(request.user)):
                logout(request)
            else:
                request.security_session = record
                if record.level != "full" and request.path not in self.PARTIAL:
                    response = JsonResponse({"status": "mfa_required"}, status=403)
                    patch_cache_control(response, no_store=True, no_cache=True, private=True)
                    response["Referrer-Policy"] = "same-origin"
                    return response
                # Conditional update cannot clear a concurrent revocation.
                now = timezone.now()
                AccountSession.objects.filter(pk=record.pk, revoked_at__isnull=True,
                    last_seen__gt=now - timedelta(seconds=settings.SECURITY_IDLE_SECONDS)).update(last_seen=now)
        marker = current_session.set(request.security_session.pk if request.security_session else None)
        try:
            response = self.get_response(request)
            if request.path.startswith("/auth/"):
                patch_cache_control(response, no_store=True, no_cache=True, private=True)
                # Chromium sends Origin:null on native form POSTs with
                # no-referrer. Keep same-origin CSRF checks and suppress
                # referrers on cross-origin navigation.
                response["Referrer-Policy"] = "same-origin"
            return response
        finally:
            current_session.reset(marker)
