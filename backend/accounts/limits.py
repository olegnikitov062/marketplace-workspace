from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.crypto import salted_hmac

from .models import AttemptBucket, AuthDenial


def denied(kind):
    AuthDenial.objects.create(kind=kind)


@transaction.atomic
def allow_attempt(action, peer, principal=None):
    """Atomic fixed windows shared by processes; no proxy-header trust.

    Counts all attempts (including successful ones). No in-process cache and
    no permanent account lock that an anonymous caller can activate.
    """
    dimensions = [("peer", peer, settings.ACCOUNT_PEER_LIMIT)]
    if principal is not None:
        dimensions.append(("principal", principal, settings.ACCOUNT_PRINCIPAL_LIMIT))
    keyed = sorted((
        salted_hmac("accounts.attempts", f"{action}:{kind}:{value}", algorithm="sha256").hexdigest(), limit,
    ) for kind, value, limit in dimensions)
    now = timezone.now()
    allowed = True
    for key, limit in keyed:
        # Unique PK resolves first-use races; select_for_update serializes count.
        AttemptBucket.objects.get_or_create(key=key)
        bucket = AttemptBucket.objects.select_for_update().get(key=key)
        if now >= bucket.window_start + timedelta(seconds=settings.ACCOUNT_ATTEMPT_WINDOW):
            bucket.window_start, bucket.attempts = now, 0
        bucket.attempts = min(bucket.attempts + 1, limit + 1)
        bucket.save(update_fields=["window_start", "attempts"])
        allowed = allowed and bucket.attempts <= limit
    return allowed
