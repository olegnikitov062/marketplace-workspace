"""Операторские действия без HTTP-доступа и без секретов в argv/выводе."""
import json
import uuid

from django.core.exceptions import ObjectDoesNotExist, PermissionDenied, ValidationError, MultipleObjectsReturned
from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError

from basework.stand_operator import execute


class Command(BaseCommand):
    help = 'Явные операции только над разрешёнными синтетическими UUID стенда'
    requires_system_checks = []

    def add_arguments(self, parser):
        parser.add_argument('action', choices=['create-user', 'bind-identity', 'grant-view', 'revoke-identity', 'revoke-view'])
        parser.add_argument('--user', type=uuid.UUID, required=True)
        parser.add_argument('--password-file')

    def handle(self, *args, **options):
        try:
            if (options['action'] == 'create-user') != bool(options['password_file']):
                raise PermissionDenied()
            result = execute(options['action'], options['user'], password_path=options['password_file'])
        except (PermissionDenied, ValidationError, ObjectDoesNotExist, MultipleObjectsReturned,
                DatabaseError, ValueError, TypeError, KeyError, OSError, AssertionError):
            raise CommandError('Операция отклонена; проверьте стенд, список UUID и историю. Секреты не выводятся.') from None
        self.stdout.write(json.dumps({'operation': options['action'], 'result': 'PASS', **result}, ensure_ascii=False))
