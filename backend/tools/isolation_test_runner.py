"""Fixed isolated suite with durable, allowlisted evidence and no raw output.

Inert import. Runtime requires the current rehearsal guard and a fresh evidence
file. No traceback messages, SQL parameters, test locals or credentials persist.
"""
import contextlib
import json
import os
import queue
import re
import subprocess
import sys
import threading
import time

LABELS = (
    'data_isolation.tests.test_context', 'data_isolation.tests.test_http',
    'data_isolation.tests.test_migrations', 'access_control.tests.test_platform',
    'access_control.tests.test_transactions', 'account_security.tests.test_http',
    'account_security.tests.test_transactions',
)


def safe_line(line):
    """Return only complete fixed unittest records; never echo unknown text."""
    line = line.strip()
    match = re.fullmatch(r'Ran (\d+) tests? in (\d+(?:\.\d+)?)s', line)
    if match:
        return {'event': 'count', 'tests': int(match[1]), 'seconds': float(match[2])}
    match = re.fullmatch(r'OK(?: \(skipped=(\d+)\))?', line)
    if match:
        return {'event': 'unittest_ok', 'skipped': int(match[1] or 0)}
    match = re.fullmatch(r'FAILED \((?:failures=\d+|errors=\d+|skipped=\d+|unexpected successes=\d+)(?:, (?:failures=\d+|errors=\d+|skipped=\d+|unexpected successes=\d+))*\)', line)
    if match:
        return {'event': 'unittest_failed'}
    match = re.fullmatch(r'(ERROR|FAIL): (test_[a-zA-Z0-9_]+) \(([a-zA-Z0-9_.]+)\)', line)
    if match:
        return {'event': 'test_failure', 'kind': match[1], 'test': match[3]}
    # Static repository test locations only, never the source line or locals.
    match = re.fullmatch(r'File "/workspace/((?:data_isolation|access_control|account_security)/tests/test_[a-z_]+\.py)", line (\d+), in ([a-zA-Z0-9_]+)', line)
    if match:
        return {'event': 'test_location', 'file': match[1], 'line': int(match[2]), 'function': match[3]}
    return None


def run(evidence):
    def emit(event):
        text = json.dumps(event, sort_keys=True)
        evidence.write(text + '\n')
        evidence.flush()
        os.fsync(evidence.fileno())
        print(text, flush=True)

    started = time.monotonic()
    emit({'event': 'suite_started', 'limit_seconds': 1750, 'failfast': True})
    process = subprocess.Popen(
        [sys.executable, 'manage.py', 'test', *LABELS, '--keepdb', '--noinput',
         '--failfast', '--verbosity=1', '--testrunner=tools.isolation_django_runner.IsolationDiscoverRunner'],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    events = queue.Queue(maxsize=100)

    def read_output():
        try:
            # Bounded memory; discard oversized/incomplete records entirely.
            while True:
                line = process.stdout.readline(8192)
                if not line:
                    break
                if not line.endswith('\n'):
                    while line and not line.endswith('\n'):
                        line = process.stdout.readline(8192)
                    continue
                event = safe_line(line)
                if event:
                    events.put(event)
        finally:
            events.put(None)

    reader = threading.Thread(target=read_output, daemon=True)
    reader.start()
    complete = False
    ok_without_skips = False
    count_seen = False
    try:
        while time.monotonic() - started < 1750:
            try:
                event = events.get(timeout=min(30, max(.1, 1750 - (time.monotonic() - started))))
            except queue.Empty:
                emit({'event': 'heartbeat', 'elapsed_seconds': int(time.monotonic() - started)})
                continue
            if event is None:
                complete = True
                break
            emit(event)
            count_seen |= event['event'] == 'count' and event['tests'] > 0
            ok_without_skips |= event['event'] == 'unittest_ok' and event['skipped'] == 0
        if not complete:
            process.kill()
        code = process.wait(timeout=5)
        success = complete and code == 0 and count_seen and ok_without_skips
        emit({'event': 'suite_finished', 'exit_code': code, 'complete': complete,
              'passed_without_skips': success, 'elapsed_seconds': int(time.monotonic() - started)})
        return 0 if success else 1
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)


def main():
    from tools.isolation_rehearsal import guard, ROOT
    # Framework startup may warn; only our structured evidence is printed.
    with open(os.devnull, 'w') as sink, contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
        guard()
    descriptor = os.open(ROOT / 'suite-events.jsonl', os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, 'w') as evidence:
        return run(evidence)


if __name__ == '__main__':
    try:
        result = main()
    except Exception:
        raise SystemExit('Isolated suite runner failed; preserve resources and sanitized evidence') from None
    raise SystemExit(result)
