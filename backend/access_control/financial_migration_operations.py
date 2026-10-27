"""Preserve existing SQLite guards across Django's offline table rebuilds."""
from django.db import migrations


class PreserveTriggers:
    def _run(self, method, app_label, editor, from_state, to_state):
        definitions = []
        if editor.connection.vendor == 'sqlite':
            with editor.connection.cursor() as cursor:
                # SQLite validates triggers on OTHER tables during a rename too.
                # Preserve every definition inside the atomic offline migration.
                cursor.execute("SELECT name,sql FROM sqlite_master WHERE type='trigger'")
                definitions = cursor.fetchall()
            for name, _ in definitions:
                editor.execute('DROP TRIGGER ' + editor.quote_name(name))
        method(app_label, editor, from_state, to_state)
        for name, definition in definitions:
            with editor.connection.cursor() as cursor:
                cursor.execute("SELECT 1 FROM sqlite_master WHERE type='trigger' AND name=%s", [name])
                exists = cursor.fetchone()
            if not exists:
                editor.execute(definition)

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        self._run(super().database_forwards, app_label, schema_editor, from_state, to_state)

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        self._run(super().database_backwards, app_label, schema_editor, from_state, to_state)


class AddConstraint(PreserveTriggers, migrations.AddConstraint):
    pass


class RemoveConstraint(PreserveTriggers, migrations.RemoveConstraint):
    pass


class AddField(PreserveTriggers, migrations.AddField):
    pass
