"""Fail closed before opening any backend other than Django locmem."""
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.core.mail import EmailMessage, get_connection
from django.core.validators import validate_email
from django.views.decorators.debug import sensitive_variables


@sensitive_variables()
def synthetic_address(value):
    value = value.strip().lower()
    validate_email(value)
    if not value.endswith("@example.invalid"):
        raise ValidationError("Only synthetic recipients are permitted")
    return value


@sensitive_variables()
def deliver(email, kind, payload):
    email = synthetic_address(email)
    backend = "django.core.mail.backends.locmem.EmailBackend"
    if settings.EMAIL_BACKEND != backend:
        raise ImproperlyConfigured("E2-05 requires locmem delivery")
    # No URL (and no request Host) is constructed; the test receiver holds a
    # credential payload in memory, consumed only by synthetic tests.
    EmailMessage(
        subject=kind, body=payload, from_email="accounts@example.invalid",
        to=[email], connection=get_connection(backend=backend),
    ).send(fail_silently=False)
