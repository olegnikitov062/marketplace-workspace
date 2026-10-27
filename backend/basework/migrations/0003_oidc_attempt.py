# Схема одноразовой попытки OIDC; применение только в разрешённом стенде.

import account_security.crypto
import django.db.models.deletion
import django.utils.timezone
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('basework', '0002_guards'),
    ]

    operations = [
        migrations.CreateModel(
            name='OIDCAttempt',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('state_hash', models.CharField(max_length=64, unique=True)),
                ('browser_hash', models.CharField(max_length=64, unique=True)),
                ('provider_hash', models.CharField(max_length=64)),
                ('nonce', account_security.crypto.EncryptedTextField()),
                ('verifier', account_security.crypto.EncryptedTextField()),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('expires_at', models.DateTimeField()),
                ('claimed_at', models.DateTimeField(null=True)),
                ('ready_at', models.DateTimeField(null=True)),
                ('finished_at', models.DateTimeField(null=True)),
                ('version', models.PositiveBigIntegerField(null=True)),
                ('credential_hash', models.CharField(default='', max_length=64)),
                ('binding', models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to='basework.identitybinding')),
            ],
        ),
    ]
