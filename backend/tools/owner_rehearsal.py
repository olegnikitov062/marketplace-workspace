"""Synthetic operator/browser rehearsal ONLY in the separately approved cluster.

Secret-bearing replies are a PRIVATE SSH pipe to the local browser runner. Never
invoke --private-pipe manually, tee its output, or use this module in main beta.
No HTTP hooks, monkeypatches, alternate MFA, or changes to operator guards.
"""
import argparse
import contextlib
import json
import os
import secrets
import stat
import subprocess
import sys
import time
from pathlib import Path

PROJECTS = frozenset({"marketplace-e206-owner-check", "marketplace-e206-owner-check-r2"})
PROJECT = os.environ.get("E206_REHEARSAL", "marketplace-e206-owner-check")
ROOT = Path("/run/rehearsal-state")
OUTPUT = Path("/run/recovery-output")
STATE = ROOT / "fixture.json"
PRIVATE = {"credentials", "token", "operator_issue"}
ACTIONS = {"configure", "init", "pre_browser", "credentials", "token", "status", "operator_prepare", "operator_issue", "block", "blocked_operator", "finish"}


def expect(value):
    if not value:
        raise RuntimeError("rehearsal_precondition_failed")


def guard():
    expect(PROJECT in PROJECTS)
    expect(os.name == "posix" and os.environ.get("E206_REHEARSAL") == PROJECT)
    marker = ROOT / "manifest.json"
    expect(marker.is_file() and not marker.is_symlink())
    expect(json.loads(marker.read_text()) == {"project": PROJECT, "synthetic_only": True})
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    expect(os.environ["DJANGO_SETTINGS_MODULE"] == "config.settings")
    import django
    django.setup()
    from django.conf import settings
    from django.db import connection
    from account_security.operator import require_operator_process
    require_operator_process()  # Real database/session_user/current_user, unchanged.
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_setting('cluster_name')")
        expect(cursor.fetchone() == (PROJECT,))
    expect(settings.EMAIL_BACKEND == "django.core.mail.backends.locmem.EmailBackend")
    expect(all(os.environ.get(k) == "false" for k in (
        "EXTERNAL_READS_ENABLED", "EXTERNAL_WRITES_ENABLED", "REAL_MESSAGES_ENABLED", "SCHEDULES_ENABLED")))


def private_file(path):
    info = path.lstat()
    expect(stat.S_ISREG(info.st_mode) and stat.S_IMODE(info.st_mode) == 0o600)
    expect(info.st_uid == os.getuid() and info.st_size <= 16384)
    return path.read_bytes()


def state():
    data = json.loads(private_file(STATE))
    expect(data["project"] == PROJECT)
    return data


def ownership():
    from ownership.models import Membership, Organization
    return {"organizations": sorted(str(pk) for pk in Organization.objects.values_list("pk", flat=True)),
            "memberships": sorted([str(row[0]), str(row[1]), row[2], row[3], str(row[4])]
                                  for row in Membership.objects.values_list("user_id", "organization_id", "role", "state", "archived_at"))}


def init():
    from django.db import transaction
    from django.utils import timezone
    from ownership.models import User, Organization, Membership
    from accounts.models import AccountContact
    from account_security.operator import write_private_new
    expect(not STATE.exists() and User.objects.count() == 0 and Organization.objects.count() == 0)
    with transaction.atomic():
        a = Organization.objects.create(name="synthetic-owner-rehearsal-a")
        b = Organization.objects.create(name="synthetic-owner-rehearsal-b")
        users = {}
        for name, organization, role in [("owner", a, "owner"), ("sessions", a, "owner"), ("other", b, "owner"), ("member", a, "observer")]:
            password = secrets.token_urlsafe(32)
            user = User.objects.create_user("synthetic-rehearsal-" + name, password)
            AccountContact.objects.create(user=user, email=name + "@example.invalid", activated_at=timezone.now())
            Membership.objects.create(user=user, organization=organization, role=role)
            users[name] = {"id": str(user.pk), "username": user.username, "password": password}
        Membership.objects.create(user_id=users["owner"]["id"], organization=b, role="observer")
        data = {"project": PROJECT, "users": users, "next_password": secrets.token_urlsafe(32), "ownership": ownership()}
        write_private_new(STATE, json.dumps(data).encode())
    return {"fixture_created": True, "users": 4, "organizations": 2}


def configure():
    from django.core.management import call_command
    from django.db import connection, transaction
    from tools.security_web_grants import apply_fresh, MAIN_ROLE
    with connection.cursor() as cursor:
        cursor.execute("SELECT to_regclass('public.django_migrations')")
        expect(cursor.fetchone() == (None,))
    call_command("migrate", interactive=False, verbosity=0)
    with transaction.atomic(), connection.cursor() as cursor:
        apply_fresh(cursor, MAIN_ROLE)
    return {"new_schema_and_exact_web_privileges": True}


def pre_browser(data):
    """Read-only gate for resuming the saved fixture before its first login.

    Never reset buckets, passwords, MFA, sessions or proof. Refuse partially
    completed browser runs instead of declaring a fresh fixture.
    """
    from ownership.models import User, Organization, Membership
    from accounts.models import AttemptBucket, Invitation
    from account_security.models import (Authenticator, AccountSession, LoginChallenge,
                                         RecoveryCode, RecoveryPermit, TrustedDevice)
    expect(User.objects.count() == 4 and Organization.objects.count() == 2 and Membership.objects.count() == 5)
    expect(ownership() == data["ownership"])
    expect(all(model.objects.count() == 0 for model in (
        AttemptBucket, Invitation, Authenticator, AccountSession, LoginChallenge,
        RecoveryCode, RecoveryPermit, TrustedDevice)))
    for values in data["users"].values():
        user = User.objects.get(pk=values["id"])
        expect(user.is_active and user.archived_at is None and user.check_password(values["password"]))
    private_file(OUTPUT / "owner-proof")
    verifier = json.loads(private_file(OUTPUT / "owner_recovery_verifier"))
    expect(verifier["user_id"] == data["users"]["owner"]["id"])
    expect(not (OUTPUT / "owner-permit").exists())
    return {"saved_fixture_before_first_login": True, "ownership_unchanged": True, "no_state_reset": True}


def cli(command, arguments, proof=None, success=True):
    """Invoke the real management CLI. PTY keeps getpass echo disabled on Linux."""
    import pty
    import select
    import termios
    argv = [sys.executable, "manage.py", command, *arguments]
    if proof is None:
        result = subprocess.run(argv, capture_output=True, timeout=45)
        expect((result.returncode == 0) == success)
        expect(b"Traceback" not in result.stderr)
        return
    master, slave = pty.openpty()
    process = None
    transcript = bytearray()
    try:
        attrs = termios.tcgetattr(slave)
        attrs[3] &= ~termios.ECHO
        termios.tcsetattr(slave, termios.TCSANOW, attrs)
        process = subprocess.Popen(argv, stdin=slave, stdout=slave, stderr=slave, start_new_session=True)
        deadline, sent = time.monotonic() + 45, False
        while time.monotonic() < deadline:
            if select.select([master], [], [], 0.2)[0]:
                try:
                    chunk = os.read(master, 4096)
                except OSError:
                    break
                transcript.extend(chunk)
                expect(len(transcript) <= 8192 and proof.encode() not in transcript)
                if not sent and b"Owner emergency secret: " in transcript:
                    expect(not termios.tcgetattr(slave)[3] & termios.ECHO)
                    os.write(master, proof.encode() + b"\n")
                    sent = True
            if process.poll() is not None:
                break
        expect(sent and process.poll() is not None)
        expect((process.returncode == 0) == success and b"Traceback" not in transcript)
    finally:
        if process is not None and process.poll() is None:
            process.kill()
            process.wait()
        os.close(master)
        os.close(slave)


def prepare(data):
    from ownership.models import User
    from account_security.models import RecoveryPermit
    owner = data["users"]["owner"]["id"]
    before = list(User.objects.order_by("pk").values_list("pk", "password", "is_active", "archived_at"))
    expect(RecoveryPermit.objects.count() == 0)
    # A non-owner cannot obtain emergency proof; actual CLI, no mocked identity.
    invalid = [str(OUTPUT / "nonowner-proof"), str(OUTPUT / "nonowner-verifier")]
    cli("prepare_owner_recovery", [data["users"]["member"]["id"], "--proof-output", invalid[0], "--verifier-output", invalid[1]], success=False)
    expect(not any(Path(p).exists() for p in invalid))
    cli("prepare_owner_recovery", [owner, "--proof-output", str(OUTPUT / "owner-proof"),
                                  "--verifier-output", str(OUTPUT / "owner_recovery_verifier")])
    private_file(OUTPUT / "owner-proof")
    expect(json.loads(private_file(OUTPUT / "owner_recovery_verifier"))["user_id"] == owner)
    expect(ownership() == data["ownership"] and RecoveryPermit.objects.count() == 0)
    expect(before == list(User.objects.order_by("pk").values_list("pk", "password", "is_active", "archived_at")))
    return {"actual_cli_prepared": True, "nonowner_denied": True, "private_files": True}


def issue(data, blocked=False):
    from ownership.models import User
    from account_security.models import RecoveryPermit, AccountSession, TrustedDevice
    owner = data["users"]["owner"]["id"]
    proof = private_file(OUTPUT / "owner-proof").decode()
    before = list(User.objects.order_by("pk").values_list("pk", "password", "is_active", "archived_at"))
    count = RecoveryPermit.objects.count()
    if blocked:
        dest = OUTPUT / "blocked-permit"
        cli("issue_owner_recovery", [owner, "--output", str(dest)], proof=proof, success=False)
        expect(not dest.exists() and RecoveryPermit.objects.count() == count)
        return {"blocked_operator_denied": True, "ownership_unchanged": ownership() == data["ownership"]}
    for name, user_id, value in [("wrong-proof", owner, secrets.token_urlsafe(32)),
                                  ("wrong-owner", data["users"]["other"]["id"], proof)]:
        dest = OUTPUT / name
        cli("issue_owner_recovery", [user_id, "--output", str(dest)], proof=value, success=False)
        expect(not dest.exists() and RecoveryPermit.objects.count() == count)
    dest = OUTPUT / "owner-permit"
    cli("issue_owner_recovery", [owner, "--output", str(dest)], proof=proof)
    expect(RecoveryPermit.objects.count() == count + 1)
    expect(not AccountSession.objects.filter(user_id=owner, revoked_at__isnull=True).exists())
    expect(not TrustedDevice.objects.filter(user_id=owner, revoked_at__isnull=True).exists())
    expect(ownership() == data["ownership"])
    expect(before == list(User.objects.order_by("pk").values_list("pk", "password", "is_active", "archived_at")))
    return {"permit": private_file(dest).decode(), "wrong_proof_denied": True, "wrong_owner_denied": True,
            "sessions_revoked": True, "ownership_and_passwords_unchanged": True}


def token(data, pending, kind, user_key):
    from django.utils import timezone
    from django_otp.oath import TOTP
    from account_security.models import Authenticator
    devices = Authenticator.objects.filter(user_id=data["users"][user_key]["id"], confirmed=not pending, revoked_at__isnull=True)
    if pending:
        devices = devices.filter(expires_at__gt=timezone.now())
    device = devices.get()
    current = int(time.time() // device.step)
    if kind == "valid" and current <= device.last_t:
        delay = (device.last_t + 1) * device.step - time.time() + 0.2
        expect(0 <= delay <= 61)
        time.sleep(delay)  # Real wall clock; never patch verifier time or last_t.
        current = int(time.time() // device.step)
    def at(tick):
        otp = TOTP(device.bin_key, device.step, device.t0, device.digits, device.drift)
        otp.time = tick * device.step + 1
        return str(otp.token()).zfill(device.digits)
    if kind == "wrong":
        valid = {at(current + offset) for offset in (-1, 0, 1)}
        value = next(str(i).zfill(device.digits) for i in range(100) if str(i).zfill(device.digits) not in valid)
    else:
        value = at(current - 4 if kind == "expired" else current)
    return {"token": value}


def status(data):
    from ownership.models import User
    from accounts.models import Invitation
    from account_security.models import AccountSecurity, Authenticator, RecoveryPermit, AccountSession, TrustedDevice
    user = User.objects.get(pk=data["users"]["owner"]["id"])
    return {"ownership_unchanged": ownership() == data["ownership"], "active": user.is_active,
            "recovery_required": AccountSecurity.objects.filter(user=user, recovery_required=True).exists(),
            "factors": Authenticator.objects.filter(user=user, confirmed=True, revoked_at__isnull=True).count(),
            "sessions": AccountSession.objects.filter(user=user, revoked_at__isnull=True).count(),
            "trusted": TrustedDevice.objects.filter(user=user, revoked_at__isnull=True).count(),
            "used_permits": RecoveryPermit.objects.filter(user=user, used_at__isnull=False).count(),
            "invitations": Invitation.objects.count()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=sorted(ACTIONS))
    parser.add_argument("--private-pipe", action="store_true")
    parser.add_argument("--pending", action="store_true")
    parser.add_argument("--user", choices=["owner", "sessions"], default="owner")
    parser.add_argument("--kind", choices=["valid", "wrong", "expired"], default="valid")
    args = parser.parse_args()
    try:
        expect(args.action not in PRIVATE or args.private_pipe and not sys.stdout.isatty())
        # Suppress incidental library/management stdout. Only deliberate JSON below.
        with open(os.devnull, "w") as sink, contextlib.redirect_stdout(sink):
            guard()
            if args.action == "configure":
                result = configure()
            elif args.action == "init":
                result = init()
            else:
                data = state()
                expect(ownership() == data["ownership"])
                if args.action == "pre_browser":
                    result = pre_browser(data)
                elif args.action == "credentials":
                    result = {"owner": data["users"]["owner"], "sessions": data["users"]["sessions"], "member": data["users"]["member"], "next_password": data["next_password"]}
                elif args.action == "token":
                    result = token(data, args.pending, args.kind, args.user)
                elif args.action == "operator_prepare":
                    result = prepare(data)
                elif args.action in {"operator_issue", "blocked_operator"}:
                    result = issue(data, args.action == "blocked_operator")
                else:
                    if args.action == "block":
                        from accounts.services import block_account
                        block_account(data["users"]["owner"]["id"])
                    result = status(data)
                    if args.action == "finish":
                        from ownership.models import User
                        expect(not result["active"] and result["sessions"] == result["trusted"] == 0)
                        expect(result["used_permits"] == 1 and result["invitations"] == 0)
                        # E2-05 block_account intentionally destroys the password.
                        # Successful login with the new password is checked by
                        # the browser before block, never after it.
                        expect(not User.objects.get(pk=data["users"]["owner"]["id"]).has_usable_password())
        print(json.dumps(result))
    except Exception:
        print("Synthetic owner rehearsal refused; preserve state; no details disclosed", file=sys.stderr)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
