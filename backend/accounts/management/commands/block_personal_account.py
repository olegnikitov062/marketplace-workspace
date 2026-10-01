from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ValidationError
from ownership.models import User
from accounts.services import block_account


class Command(BaseCommand):
    help = "Trusted operator: block one synthetic personal account; no unblock or tenant scope changes."

    def add_arguments(self, parser):
        parser.add_argument("user_id")

    def handle(self, *args, **options):
        try:
            block_account(options["user_id"])
        except (User.DoesNotExist, ValidationError, ValueError):
            raise CommandError("Operation denied") from None
        self.stdout.write("Account blocked; prior credentials invalidated")
