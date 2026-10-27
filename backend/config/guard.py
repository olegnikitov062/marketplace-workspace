"""Validate effective configuration before reading credentials or opening a connection."""
import os
from pathlib import Path, PurePosixPath

class ConfigurationError(ValueError):
    pass

DISABLED = ("EXTERNAL_READS_ENABLED", "EXTERNAL_WRITES_ENABLED", "REAL_MESSAGES_ENABLED", "SCHEDULES_ENABLED")
FORBIDDEN = ("DATABASE_URL", "SOURCE_DATABASE_URL", "WB_TOKEN", "SMTP_HOST", "EMAIL_HOST", "SOURCE_URL")

def validate(env):
    name = env.get("ENVIRONMENT", "")
    if name not in {"local", "beta"}:
        raise ConfigurationError("ENVIRONMENT must be local or beta; production is not authorized")
    mode = env.get("PROCESS_MODE", "web")
    if mode not in {"web", "migrate", "test"}:
        raise ConfigurationError("PROCESS_MODE must be web, migrate or test")
    for key in DISABLED:
        if env.get(key, "false") != "false":
            raise ConfigurationError(key + " must be false")
    if any(env.get(key) for key in FORBIDDEN):
        raise ConfigurationError("Source, SMTP and arbitrary database connections are forbidden")
    prefix = "mw_" + name
    expected = {
        "DB_HOST": "postgres-test" if mode == "test" else "postgres",
        "DB_PORT": "5432",
        "DB_NAME": prefix + "_test" if mode == "test" else prefix,
        "DB_USER": prefix + ("_test_runner" if mode == "test" else "_migrator" if mode == "migrate" else "_web"),
    }
    for key, value in expected.items():
        if env.get(key) != value:
            raise ConfigurationError(key + " does not match the selected environment/process")
    for key in ("DB_PASSWORD_FILE", "DJANGO_SECRET_KEY_FILE"):
        path = PurePosixPath(env.get(key, ""))
        if not path.is_absolute() or path.parent != PurePosixPath("/run/secrets") or path.name in {"", ".", ".."}:
            raise ConfigurationError(key + " must name a file in /run/secrets")
    expected_secret = "db_test_runner_password" if mode == "test" else "db_migrator_password" if mode == "migrate" else "db_web_password"
    if env["DB_PASSWORD_FILE"] != "/run/secrets/" + expected_secret:
        raise ConfigurationError("Wrong database credential for this process")
    if env["DJANGO_SECRET_KEY_FILE"] != "/run/secrets/django_secret_key":
        raise ConfigurationError("Wrong Django key path")
    return {"environment": name, "mode": mode, **expected}

def secret(path):
    value = Path(path).read_text(encoding="utf-8").strip()
    if len(value) < 32:
        raise ConfigurationError("Missing or short process secret")
    return value
