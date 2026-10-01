from django.apps import AppConfig


class AccountSecurityConfig(AppConfig):
    name = "account_security"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        from . import signals  # noqa: F401
