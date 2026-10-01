import json
import secrets
from pathlib import Path

from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.views.decorators.debug import sensitive_variables

from account_security.operator import require_operator_process, write_private_new
from account_security.services import locked_user, required, event


class Command(BaseCommand):
    help = "Provision separate owner emergency proof into two private NEW files; no values on stdout."

    def add_arguments(self, parser):
        parser.add_argument("user_id")
        parser.add_argument("--proof-output", required=True)
        parser.add_argument("--verifier-output", required=True)

    @sensitive_variables()
    def handle(self, *args, **options):
        try:
            require_operator_process()
            paths = [Path(options[name]) for name in ("proof_output", "verifier_output")]
            if paths[0] == paths[1] or any(not p.is_absolute() or p.parent.resolve() != Path("/run/recovery-output")
                or p.exists() or p.is_symlink() for p in paths):
                raise PermissionDenied()
            with transaction.atomic():
                user, _ = locked_user(options["user_id"])
                if not required(user):
                    raise PermissionDenied()
                raw = secrets.token_urlsafe(32)
                verifier = json.dumps({"user_id": str(user.pk), "verifier": make_password(raw)}).encode()
                write_private_new(paths[0], raw.encode())
                write_private_new(paths[1], verifier)
                event(user, "operator_proof_prepared")
            self.stdout.write("Separate proof and verifier prepared. Retain partial outputs on failure; no delivery performed.")
        except Exception:
            raise CommandError("Owner proof preparation denied; preserve any created files") from None
