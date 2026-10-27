"""Allowlisted restore progress only; never persist SQL, rows or exceptions."""
import json
import os


STAGES = frozenset(('guard', 'source_acl', 'restore_connect', 'restore_identity',
                    'metadata', 'rows', 'sequences', 'revoked_fixture',
                    'immutable_guard', 'quarantine', 'quarantine_verify'))


class RestoreEvidence:
    def __init__(self, path):
        self.path = path
        self.stage = 'guard'
        self.index = 0

    def __enter__(self):
        descriptor = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        self.output = os.fdopen(descriptor, 'w')
        return self

    def emit(self, event):
        line = json.dumps({'event': event, 'stage': self.stage, 'index': self.index}, sort_keys=True)
        self.output.write(line + '\n')
        self.output.flush()
        os.fsync(self.output.fileno())
        print(line, flush=True)

    def checkpoint(self, stage, index=0):
        if stage not in STAGES or type(index) is not int or not 0 <= index <= 1000:
            raise ValueError('invalid_restore_evidence_stage')
        self.stage, self.index = stage, index
        self.emit('restore_stage_started')

    def __exit__(self, kind, value, traceback):
        try:
            self.emit('restore_failed' if kind is not None else 'restore_passed')
        finally:
            self.output.close()
        # Deliberately do not inspect, stringify or suppress the exception.
        return False
