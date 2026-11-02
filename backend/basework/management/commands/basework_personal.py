"""Адресная подготовка личных аккаунтов по закрытому операторскому списку."""
import json
import uuid

from django.core.management.base import BaseCommand, CommandError
from django.views.decorators.debug import sensitive_variables

from basework.personal_access import execute


class Command(BaseCommand):
    help = 'Личный аккаунт BaseWork: создание, код доступа, допуск или отзыв FAQ/переговорок'
    requires_system_checks = []

    def add_arguments(self, parser):
        parser.add_argument('action', choices=['create', 'issue-access', 'grant', 'revoke', 'grant-admin', 'revoke-admin'])
        parser.add_argument('--user', type=uuid.UUID, required=True)
        parser.add_argument('--output')

    @sensitive_variables()
    def handle(self, *args, **options):
        try:
            result = execute(options['action'], options['user'], output=options['output'])
        except Exception:
            raise CommandError('Операция отклонена. Проверьте роль, список пользователей и состояние аккаунта. '
                               'Существующий выходной файл сохранён; не повторяйте операцию без сверки.') from None
        self.stdout.write(json.dumps(result, ensure_ascii=False))
