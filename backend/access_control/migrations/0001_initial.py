import django.db.models.deletion
import django.utils.timezone
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('account_security', '0002_revocation_guards'),
        ('ownership', '0002_postgresql_ownership_guards'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='PlatformRoleAssignment',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('revoked_at', models.DateTimeField(blank=True, null=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Grant',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('resource', models.CharField(choices=[('memberships', 'Memberships'), ('synthetic_record', 'Record')], max_length=24)),
                ('action', models.CharField(choices=[('view', 'View'), ('export', 'Export'), ('change', 'Change'), ('manage_access', 'Manage')], max_length=16)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('revoked_at', models.DateTimeField(blank=True, null=True)),
                ('cabinet', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='ownership.cabinet')),
                ('membership', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='ownership.membership')),
                ('organization', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='ownership.organization')),
                ('platform', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='access_control.platformroleassignment')),
            ],
        ),
        migrations.CreateModel(
            name='SupportWindow',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('reason', models.CharField(choices=[('synthetic_diagnostic', 'Synthetic diagnostic')], max_length=24)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('expires_at', models.DateTimeField()),
                ('revoked_at', models.DateTimeField(blank=True, null=True)),
                ('grant', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='access_control.grant')),
                ('session', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='account_security.accountsession')),
            ],
        ),
        migrations.CreateModel(
            name='SyntheticRecord',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('value', models.IntegerField(default=0)),
                ('archived_at', models.DateTimeField(blank=True, null=True)),
                ('cabinet', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='ownership.cabinet')),
                ('organization', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='ownership.organization')),
            ],
        ),
        migrations.CreateModel(
            name='ExportBinding',
            fields=[
                ('permit', models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, primary_key=True, serialize=False, to='account_security.exportpermit')),
                ('grant', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='access_control.grant')),
                ('record', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='access_control.syntheticrecord')),
            ],
        ),
        migrations.AddConstraint(
            model_name='platformroleassignment',
            constraint=models.UniqueConstraint(condition=models.Q(('revoked_at__isnull', True)), fields=('user',), name='access_one_platform_assignment'),
        ),
        migrations.AddConstraint(
            model_name='grant',
            constraint=models.CheckConstraint(condition=models.Q(models.Q(('membership__isnull', False), ('platform__isnull', True)), models.Q(('membership__isnull', True), ('platform__isnull', False)), _connector='OR'), name='access_one_subject'),
        ),
        migrations.AddConstraint(
            model_name='grant',
            constraint=models.CheckConstraint(condition=models.Q(models.Q(('action__in', ['view', 'manage_access']), ('cabinet__isnull', True), ('resource', 'memberships')), models.Q(('action__in', ['view', 'export', 'change', 'manage_access']), ('resource', 'synthetic_record')), _connector='OR'), name='access_known_operation'),
        ),
    ]
