"""Print the exact plan; --apply creates only fresh isolated rehearsal files.

Linux execution requires this script in an immutable, published beta Git release.
No container services are started, no database is modified, no secret is printed.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

PROJECT = "marketplace-e209-20261007-01a115d9-r2"
BETA = Path("/home/adm_user/marketplace-workspace/beta")
PROFILES = {PROJECT: "e2-09-20261007-01a115d9-r2"}
ROOT = BETA / "rehearsals" / PROFILES[PROJECT]
LOCK_SHA256 = "35cba592050150a0e5b1f68adc36d3f1c0871ceec79efc6c7f8e4a925fb34e60"
IMAGE = "sha256:86f9cac63025d6c6119d2f7e0b232004b3ebfe98a82800a672bef73fdd1fbe72"
POSTGRES = "sha256:248efd5e58cd743f2a0e0daec8ea4649e5580145ec2a12e2345bc710d4a77201"
NAMES = [PROJECT + "-" + service for service in ("postgres", "web", "controller")]


def command(*args):
    return subprocess.check_output(args, stderr=subprocess.DEVNULL).decode().strip()


def protected_rehearsal():
    result = []
    for project in ('marketplace-e206-owner-check', 'marketplace-e206-owner-check-r2', 'marketplace-e207-20261005-01a10b2d'):
        services = ('postgres', 'web', 'controller') if project.startswith('marketplace-e207-') else ('postgres', 'web', 'controller', 'issuer')
        names = [project + '-' + service for service in services]
        rows = json.loads(command('docker', 'inspect', *names))
        if any(row['State']['Running'] or row['Config']['Labels'].get('com.docker.compose.project') != project for row in rows):
            raise RuntimeError()
        result.extend({'id': row['Id'], 'image': row['Image'], 'started': row['State']['StartedAt'],
            'mounts': sorted(row['Mounts'], key=lambda mount: mount['Destination']),
            'networks': sorted(row['NetworkSettings']['Networks']), 'ports': row['NetworkSettings']['Ports']} for row in rows)
    # The first E2-08 attempt stopped during configure; only postgres persists.
    project = 'marketplace-e208-20261006-01a1105a'
    row = json.loads(command('docker', 'inspect', project + '-postgres'))[0]
    if row['State']['Running'] or row['Config']['Labels'].get('com.docker.compose.project') != project:
        raise RuntimeError()
    result.append({'id': row['Id'], 'image': row['Image'], 'started': row['State']['StartedAt'],
        'mounts': sorted(row['Mounts'], key=lambda mount: mount['Destination']),
        'networks': sorted(row['NetworkSettings']['Networks']), 'ports': row['NetworkSettings']['Ports']})
    # R2/R3 stopped during their suites; neither web was created.
    for project in ('marketplace-e208-20261007-01a1105a-r2', 'marketplace-e208-20261007-01a1105a-r3'):
        for service in ('postgres', 'controller'):
            row = json.loads(command('docker', 'inspect', project + '-' + service))[0]
            if row['State']['Running'] or row['Config']['Labels'].get('com.docker.compose.project') != project:
                raise RuntimeError()
            result.append({'id': row['Id'], 'image': row['Image'], 'started': row['State']['StartedAt'],
                'mounts': sorted(row['Mounts'], key=lambda mount: mount['Destination']),
                'networks': sorted(row['NetworkSettings']['Networks']), 'ports': row['NetworkSettings']['Ports']})
    project = 'marketplace-e208-20261007-01a1105a-r4'
    for service in ('postgres', 'web', 'controller'):
        row = json.loads(command('docker','inspect',project+'-'+service))[0]
        if row['State']['Running'] or row['Config']['Labels'].get('com.docker.compose.project') != project:
            raise RuntimeError()
        result.append({'id':row['Id'],'image':row['Image'],'started':row['State']['StartedAt'],
            'mounts':sorted(row['Mounts'],key=lambda m:m['Destination']),
            'networks':sorted(row['NetworkSettings']['Networks']),'ports':row['NetworkSettings']['Ports']})
    # R1 stopped during its suite. Preserve both containers; no web was created.
    project = 'marketplace-e209-20261007-01a115d9-r1'
    for service in ('postgres', 'controller'):
        row = json.loads(command('docker','inspect',project+'-'+service))[0]
        if row['State']['Running'] or row['Config']['Labels'].get('com.docker.compose.project') != project:
            raise RuntimeError()
        result.append({'id':row['Id'],'image':row['Image'],'started':row['State']['StartedAt'],
            'mounts':sorted(row['Mounts'],key=lambda m:m['Destination']),
            'networks':sorted(row['NetworkSettings']['Networks']),'ports':row['NetworkSettings']['Ports']})
    return result


def plan():
    return {"project": PROJECT, "root": ROOT.as_posix(), "network": PROJECT + "-private",
            "volume": PROJECT + "-data", "containers": NAMES, "image": IMAGE, "postgres_image": POSTGRES,
            "ports": [], "source": "published immutable Git release/backend read-only",
            "keys": "new synthetic files only; no main/test-beta secret mounts", "default_action": "print plan"}


def apply(revision):
    if os.name != "posix" or not re.fullmatch(r"[0-9a-f]{40}", revision or ""):
        raise RuntimeError()
    release = BETA / "app/releases" / revision
    published = command('git', '-C', str(release), 'ls-remote', '--heads', 'origin', 'beta').split()[0]
    if not re.fullmatch(r'[0-9a-f]{40}', published):
        raise RuntimeError()
    subprocess.run(['git','-C',str(release),'merge-base','--is-ancestor',revision,published],
                   check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    import hashlib
    if hashlib.sha256((release/'backend/requirements.lock').read_bytes()).hexdigest() != LOCK_SHA256:
        raise RuntimeError()
    if Path(__file__).resolve().parents[2] != release or command("git", "-C", str(release), "rev-parse", "HEAD") != revision:
        raise RuntimeError()
    if command("git", "-C", str(release), "status", "--porcelain") or ROOT.exists() or ROOT.is_symlink():
        raise RuntimeError()
    subprocess.run(["git", "-C", str(BETA / "app/repository"), "merge-base", "--is-ancestor", revision, "origin/beta"],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for kind, names in [("container", NAMES), ("network", [PROJECT + "-private"]), ("volume", [PROJECT + "-data"])]:
        for name in names:
            result = subprocess.run(["docker", kind, "inspect", name], capture_output=True)
            # Docker daemon must be alive; the fixed resource must not exist.
            command("docker", "info", "--format", "{{.ServerVersion}}")
            if result.returncode == 0:
                raise RuntimeError()
    if command("docker", "ps", "-aq", "--filter", "label=com.docker.compose.project=" + PROJECT):
        raise RuntimeError()
    memory = next(int(line.split()[1]) for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:'))
    if shutil.disk_usage(BETA).free < 2 * 1024**3 or memory < 2048 * 1024:
        raise RuntimeError()
    for image in (IMAGE, POSTGRES):
        if command("docker", "image", "inspect", "--format", "{{.Id}}", image) != image:
            raise RuntimeError()
    pg_uid = int(command("docker", "run", "--rm", "--pull", "never", "--network", "none", "--read-only", "--entrypoint", "id", POSTGRES, "-u", "postgres"))
    baseline_ids = command("docker", "ps", "--no-trunc", "-q", "--filter", "label=com.docker.compose.project=marketplace-beta").split()
    if len(baseline_ids) != 3:
        raise RuntimeError()
    rows = json.loads(command("docker", "inspect", *baseline_ids))
    web = [row for row in rows if row['Config']['Labels'].get('com.docker.compose.service') == 'web']
    if len(web) != 1 or web[0]['Image'] != IMAGE:
        raise RuntimeError()
    source_mounts = [mount for mount in web[0]['Mounts'] if mount['Destination'] == '/workspace']
    expected_source = str(BETA / 'app/releases/409c71f65db53873183c6ffd8d059561c05185d2/backend')
    if len(source_mounts) != 1 or source_mounts[0]['Source'] != expected_source or source_mounts[0]['RW']:
        raise RuntimeError()
    baseline = [{"id": x["Id"], "image": x["Image"], "started": x["State"]["StartedAt"],
                 "mounts": sorted(x["Mounts"], key=lambda m: m["Destination"]),
                 "networks": sorted(x["NetworkSettings"]["Networks"]), "ports": x["NetworkSettings"]["Ports"]} for x in rows]
    preserved = protected_rehearsal()
    if ROOT.parent.exists() and ROOT.parent.is_symlink():
        raise RuntimeError()
    ROOT.parent.mkdir(mode=0o700, exist_ok=True)
    ROOT.mkdir(mode=0o700)
    for name in ("secrets", "state", "operator-output", "backups"):
        (ROOT / name).mkdir(mode=0o700)
    code = """import os,secrets,json
from pathlib import Path
from cryptography.fernet import Fernet
def write(path,data,uid=10001):
 with os.fdopen(os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'wb') as out:out.write(data)
 os.chown(path,uid,uid)
root=Path('/rehearsal')
admin=secrets.token_urlsafe(48).encode()
write(root/'secrets/db_bootstrap_password',admin)
write(root/'secrets/pg_bootstrap_password',admin,PG_UID)
for name in ['db_migrator_password','db_web_password','django_secret_key']:
 write(root/'secrets'/name,secrets.token_urlsafe(48).encode())
write(root/'secrets/mfa_encryption_key',Fernet.generate_key())
write(root/'secrets/isolation_signing_key',secrets.token_bytes(32))
write(root/'state/manifest.json',json.dumps({'project':PROJECT_NAME,'synthetic_only':True}).encode())
for name in ['secrets','state','operator-output']:os.chown(root/name,10001,10001)
os.chown(root/'backups',PG_UID,PG_UID)
""".replace("PG_UID", str(pg_uid)).replace("PROJECT_NAME", repr(PROJECT))
    result = subprocess.run(["docker", "run", "--rm", "-i", "--pull", "never", "--network", "none", "--read-only", "--memory", "128m",
        "--pids-limit", "64", "--cpus", "0.25", "--log-driver", "none", "--cap-drop", "ALL", "--cap-add", "CHOWN", "--cap-add", "DAC_OVERRIDE",
        "--security-opt", "no-new-privileges:true", "--user", "0:0", "--mount", f"type=bind,src={ROOT},dst=/rehearsal",
        IMAGE, "python", "-"], input=code.encode(), capture_output=True)
    if result.returncode:
        raise RuntimeError()
    with os.fdopen(os.open(ROOT / "baseline.json", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w") as out:
        json.dump(baseline, out)
    if preserved is not None:
        with os.fdopen(os.open(ROOT / "preserved-rehearsal.json", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w") as out:
            json.dump(preserved, out)
    print("Synthetic rehearsal files prepared; existing beta unchanged; do not repeat or remove partial files")


def verify(revision):
    if os.name != "posix" or not re.fullmatch(r"[0-9a-f]{40}", revision or ""):
        raise RuntimeError()
    source = BETA / "app/releases" / revision / "backend"
    if json.loads((ROOT / "preserved-rehearsal.json").read_text()) != protected_rehearsal():
        raise RuntimeError()
    baseline = json.loads((ROOT / "baseline.json").read_text())
    ids = command("docker", "ps", "--no-trunc", "-q", "--filter", "label=com.docker.compose.project=marketplace-beta").split()
    if set(ids) != {row['id'] for row in baseline}:
        raise RuntimeError()
    for current in json.loads(command("docker", "inspect", *ids)):
        before = next(row for row in baseline if row['id'] == current['Id'])
        if before != {"id": current['Id'], "image": current['Image'], "started": current['State']['StartedAt'],
                      "mounts": sorted(current['Mounts'], key=lambda m: m['Destination']),
                      "networks": sorted(current['NetworkSettings']['Networks']), "ports": current['NetworkSettings']['Ports']}:
            raise RuntimeError()
    network = json.loads(command("docker", "network", "inspect", PROJECT + "-private"))[0]
    if not network['Internal']:
        raise RuntimeError()
    for row in json.loads(command("docker", "inspect", *NAMES)):
        if row['Config']['Labels'].get('com.docker.compose.project') != PROJECT or row['HostConfig']['Privileged']:
            raise RuntimeError()
        if sorted(row['NetworkSettings']['Networks']) != [PROJECT + '-private'] or any(row['NetworkSettings']['Ports'].values()):
            raise RuntimeError()
        if row['Name'].endswith('-postgres'):
            if row['Image'] != POSTGRES:
                raise RuntimeError()
            continue
        if row['Image'] != IMAGE or row['Config']['User'] != '10001:10001' or not row['HostConfig']['ReadonlyRootfs']:
            raise RuntimeError()
        code = next(m for m in row['Mounts'] if m['Destination'] == '/workspace')
        if code['Source'] != str(source) or code['RW']:
            raise RuntimeError()
        if any(m['Type'] == 'bind' and m['Destination'] != '/workspace' and not m['Source'].startswith(str(ROOT) + '/') for m in row['Mounts']):
            raise RuntimeError()
        if row['Name'].endswith('-web'):
            targets = {m['Destination'] for m in row['Mounts'] if m['Type'] == 'bind'}
            if targets != {'/workspace', '/run/rehearsal-state', '/run/secrets/db_web_password', '/run/secrets/django_secret_key', '/run/secrets/mfa_encryption_key', '/run/secrets/isolation_signing_key'}:
                raise RuntimeError()
        else:
            targets = {m['Destination'] for m in row['Mounts'] if m['Type'] == 'bind'}
            allowed = {'/workspace', '/run/rehearsal-state', '/run/secrets/db_migrator_password',
                       '/run/secrets/django_secret_key', '/run/secrets/mfa_encryption_key', '/run/secrets/db_web_password', '/run/secrets/isolation_signing_key'}
            if row['Name'].endswith('-issuer'):
                allowed.add('/run/secrets/owner_recovery_verifier')
            if targets != allowed:
                raise RuntimeError()
        if any(m['RW'] for m in row['Mounts'] if m['Destination'].startswith('/run/secrets/')):
            raise RuntimeError()
    print('Rehearsal isolation and unchanged main beta container metadata verified')


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--apply", action="store_true")
    group.add_argument("--verify", action="store_true")
    parser.add_argument("--revision")
    parser.add_argument("--project", choices=sorted(PROFILES), default=PROJECT)
    args = parser.parse_args()
    PROJECT = args.project
    ROOT = BETA / "rehearsals" / PROFILES[PROJECT]
    NAMES = [PROJECT + "-" + service for service in ("postgres", "web", "controller")]
    if not args.apply and not args.verify:
        print(json.dumps(plan(), indent=2))
    else:
        try:
            (verify if args.verify else apply)(args.revision)
        except Exception:
            raise SystemExit("Rehearsal preparation refused; preserve any created resources; no details disclosed") from None
