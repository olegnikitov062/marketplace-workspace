# Схема BaseWork, сформирована Django 5.2.17; только изолированные локальные проверки.

import django.db.models.deletion
import django.utils.timezone
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('account_security', '0002_revocation_guards'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='IdentityBinding',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('issuer', models.CharField(max_length=512)),
                ('subject', models.CharField(max_length=255)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('revoked_at', models.DateTimeField(blank=True, null=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='FederatedSession',
            fields=[
                ('session', models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, primary_key=True, serialize=False, to='account_security.accountsession')),
                ('binding', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='basework.identitybinding')),
            ],
        ),
        migrations.CreateModel(
            name='ApplicationAccess',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('application', models.CharField(choices=[('marketplace', 'marketplace'), ('reports', 'reports'), ('sources', 'sources'), ('airflow', 'airflow'), ('bloggers', 'bloggers'), ('faq', 'faq'), ('rooms', 'rooms')], max_length=24)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('revoked_at', models.DateTimeField(blank=True, null=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'constraints': [models.CheckConstraint(condition=models.Q(('application__in', ('marketplace', 'reports', 'sources', 'airflow', 'bloggers', 'faq', 'rooms'))), name='basework_known_application'), models.UniqueConstraint(condition=models.Q(('revoked_at__isnull', True)), fields=('user', 'application'), name='basework_one_application_access')],
            },
        ),
        migrations.AddConstraint(
            model_name='identitybinding',
            constraint=models.UniqueConstraint(fields=('issuer', 'subject'), name='basework_identity_unique'),
        ),
        migrations.AddConstraint(
            model_name='identitybinding',
            constraint=models.CheckConstraint(condition=models.Q(models.Q(('issuer', ''), _negated=True), models.Q(('subject', ''), _negated=True)), name='basework_identity_nonempty'),
        ),
    ]
