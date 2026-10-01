import getpass
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.views.decorators.debug import sensitive_variables

from account_security.operator import require_operator_process, verify_owner_proof, write_private_new
from account_security.services import issue_operator_recovery


class Command(BaseCommand):
    help = "Explicit owner MFA recovery; separately authorized operator process only."

    def add_arguments(self, parser):
        parser.add_argument("user_id")
        parser.add_argument("--output", required=True)

    @sensitive_variables()
    def handle(self, *args, **options):
        try:
            require_operator_process()
            output = Path(options["output"])
            if (not output.is_absolute() or output.parent.resolve() != Path("/run/recovery-output")
                    or output.exists() or output.is_symlink()):
                raise PermissionDenied()
            proof = getpass.getpass("Owner emergency secret: ")
            if not verify_owner_proof(options["user_id"], proof, "/run/secrets/owner_recovery_verifier"):
                raise PermissionDenied()
            with transaction.atomic():
                token = issue_operator_recovery(options["user_id"])
                write_private_new(output, token.encode())
            self.stdout.write("Recovery permit created. It permits MFA enrollment only and expires in five minutes.")
        except Exception:
            raise CommandError("Owner recovery denied; preserve any created output and inspect state without logging values.") from None
