"""Explicit offline operator proof; no HTTP endpoint and no embedded emergency key."""
import json
import os
from pathlib import Path

from django.conf import settings
from django.contrib.auth.hashers import check_password
from django.core.exceptions import PermissionDenied
from django.db import connection
from django.views.decorators.debug import sensitive_variables


def require_operator_process():
    effective = getattr(settings, "EFFECTIVE", {})
    if effective.get("environment") != "beta" or effective.get("mode") != "migrate":
        raise PermissionDenied()
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_database(), session_user, current_user")
        if cursor.fetchone() != ("mw_beta", "mw_beta_migrator", "mw_beta_migrator"):
            raise PermissionDenied()


@sensitive_variables()
def verify_owner_proof(user_id, proof, verifier_path):
    try:
        record = json.loads(Path(verifier_path).read_text(encoding="utf-8"))
        return (str(record["user_id"]) == str(user_id) and len(proof) >= 32
                and check_password(proof, record["verifier"]))
    except (OSError, KeyError, ValueError, TypeError):
        return False


@sensitive_variables()
def write_private_new(path, data):
    """Never overwrite/symlink-follow an existing credential output."""
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        # Preserve a partial file for investigation; do not silently regenerate.
        raise
