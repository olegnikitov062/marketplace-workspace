"""Provisional synthetic E2-05 settings; not accepted production policy."""

SESSION_ENGINE = "django.contrib.sessions.backends.db"
AUTHENTICATION_BACKENDS = ["accounts.backends.PersonalAccountBackend"]
PASSWORD_RESET_TIMEOUT = 30 * 60
ACCOUNT_INVITATION_TTL = 24 * 60 * 60
ACCOUNT_ATTEMPT_WINDOW = 15 * 60
ACCOUNT_PRINCIPAL_LIMIT = 5
ACCOUNT_PEER_LIMIT = 30
SESSION_COOKIE_AGE = 8 * 60 * 60
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 12}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
