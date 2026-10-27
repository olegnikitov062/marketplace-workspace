from django.dispatch import receiver
from django_otp.forms import otp_verification_failed
from accounts.limits import denied


@receiver(otp_verification_failed, dispatch_uid="security_totp_denied")
def factor_denied(sender, **kwargs):
    denied("totp_denied")
