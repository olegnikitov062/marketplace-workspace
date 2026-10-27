from django.core.management.base import BaseCommand, CommandError
from access_control import operator


class Command(BaseCommand):
    help = 'Explicit beta migrator-only access provisioning; no credentials or identities on stdout.'

    def add_arguments(self, parser):
        parser.add_argument('operation', choices=['assign-platform', 'revoke-platform', 'grant-platform', 'revoke-platform-grant', 'bootstrap-owner', 'bootstrap-finance', 'promote-owner', 'demote-owner'])
        parser.add_argument('subject_id')
        parser.add_argument('--organization-id')
        parser.add_argument('--resource')
        parser.add_argument('--action')
        parser.add_argument('--cabinet-id')

    def handle(self, *args, **options):
        try:
            op = options['operation']
            if op == 'grant-platform':
                operator.grant_platform(options['subject_id'], options['organization_id'], options['resource'], options['action'], options['cabinet_id'])
            elif op in ('promote-owner', 'demote-owner'):
                operator.change_owner(options['subject_id'], op == 'promote-owner')
            else:
                {'assign-platform': operator.assign_platform, 'revoke-platform': operator.revoke_platform,
                 'bootstrap-owner': operator.bootstrap_owner, 'bootstrap-finance': operator.bootstrap_finance,
                 'revoke-platform-grant': operator.revoke_platform_grant}[op](options['subject_id'])
        except Exception:
            raise CommandError('Access operator operation denied; no changes committed.') from None
        self.stdout.write('Access operator operation completed.')
