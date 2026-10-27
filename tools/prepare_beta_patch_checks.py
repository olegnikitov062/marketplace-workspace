"""Render a fresh, synthetic PostgreSQL 17 rehearsal. Never contacts a server.

The generated Linux kit requires an isolated Docker host, not permanent Selectel.
No secrets, containers or databases are created by this renderer.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil

REPO = Path(__file__).resolve().parents[1]
OLD_PROJECT = 'marketplace-e209-20261007-01a115d9-r4'
OLD_ROOT = '/home/adm_user/marketplace-workspace/beta/rehearsals/e2-09-20261007-01a115d9-r4'

PREPARE = r'''import base64,json,os,secrets,subprocess
from pathlib import Path
root=Path(__file__).resolve().parent
assert os.name=='posix' and os.geteuid()==0, 'Linux root required for synthetic file ownership'
os.chdir(root)
cfg=json.loads((root/'compose.json').read_text())
project=cfg['name']
names=subprocess.check_output(['docker','ps','-a','--format','{{.Names}}'],text=True).splitlines()
assert 'closed-beta-web' not in names, 'Permanent Selectel host is excluded'
assert not any(n.startswith(project) for n in names), 'Existing rehearsal containers'
for kind,suffix in [('network','private'),('volume','data')]:
 r=subprocess.run(['docker',kind,'inspect',project+'-'+suffix],capture_output=True)
 assert r.returncode!=0, 'Existing rehearsal resource'
assert not any((root/n).exists() for n in ['secrets','state','backups']), 'Existing state; preserve it'
for n in ['secrets','state','backups']:(root/n).mkdir(mode=0o700)
pg=cfg['services']['postgres']['image']
uid=int(subprocess.check_output(['docker','run','--rm','--network','none','--pull','never',pg,'id','-u','postgres']))
def put(name,data,owner=10001):
 p=root/name
 with os.fdopen(os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'wb') as f:f.write(data)
 os.chown(p,owner,owner)
admin=secrets.token_urlsafe(48).encode()
put('secrets/db_bootstrap_password',admin)
put('secrets/pg_bootstrap_password',admin,uid)
for name in ['db_migrator_password','db_web_password','django_secret_key']:
 put('secrets/'+name,secrets.token_urlsafe(48).encode())
put('secrets/mfa_encryption_key',base64.urlsafe_b64encode(secrets.token_bytes(32)))
put('secrets/isolation_signing_key',secrets.token_bytes(32))
put('state/manifest.json',json.dumps({'project':project,'synthetic_only':True}).encode())
for name in ['state','secrets']:os.chown(root/name,10001,10001)
os.chown(root/'backups',uid,uid)
print('Fresh synthetic files prepared; no application containers started')
'''

UPGRADE = r'''"""Synthetic checkpoint only; data never printed. Migrator on guarded test cluster."""
import json,os,sys
from pathlib import Path
from tools.financial_rehearsal import guard,expect,ROOT
def snapshot():
 from django.db import connection
 from tools.financial_restore_check import METADATA
 from psycopg import sql
 result={'metadata':[],'tables':{},'sequences':{}}
 with connection.cursor() as c:
  for query in METADATA:
   c.execute(query); result['metadata'].append(c.fetchall())
  c.execute(METADATA[0]); tables=c.fetchall()
  for schema,table in tables:
   c.execute(sql.SQL('SELECT row_to_json(t)::text FROM {} t ORDER BY row_to_json(t)::text').format(sql.Identifier(schema,table)))
   result['tables'][schema+'.'+table]=c.fetchall()
  c.execute("SELECT schemaname,sequencename FROM pg_sequences WHERE schemaname='public' ORDER BY 1,2")
  for schema,name in c.fetchall():
   c.execute(sql.SQL('SELECT last_value,is_called FROM {}').format(sql.Identifier(schema,name)))
   result['sequences'][schema+'.'+name]=c.fetchall()
 return json.loads(json.dumps(result,default=str))
try:
 guard(); p=ROOT/'synthetic-upgrade-checkpoint.json'
 if sys.argv[1]=='before':
  with os.fdopen(os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'w') as f:json.dump(snapshot(),f)
 else:
  from django.core.management import call_command
  from django.db import connection
  from django.db.migrations.executor import MigrationExecutor
  executor=MigrationExecutor(connection)
  expect(not executor.migration_plan(executor.loader.graph.leaf_nodes()))
  call_command('migrate',interactive=False,verbosity=0)
  expect(json.loads(p.read_text())==snapshot())
  print('Patch upgrade: no pending schema change; rows, sequences, ACL and RLS unchanged: PASS')
except Exception:
 raise SystemExit('Patch checkpoint failed; preserve synthetic state; details suppressed') from None
'''

RUN = r'''#!/bin/sh
set -eu
cd "$(dirname "$0")"
# This script is ONLY for an isolated Linux Docker host. Never the permanent server.
test "$(id -u)" = 0
if docker ps -a --format '{{.Names}}' | grep -qx closed-beta-web; then
  echo 'Permanent Selectel host excluded'; exit 1
fi
dc() { docker compose --env-file /dev/null -f compose.json "$@"; }
test ! -e image-ids.txt
test ! -e state
finish() {
  code=$?
  trap - EXIT
  if [ "${STARTED:-0}" = 1 ]; then dc stop web controller postgres >/dev/null 2>&1 || true; fi
  exit "$code"
}
trap finish EXIT
trap 'exit 1' HUP INT TERM
docker pull __PG__
docker build --platform linux/amd64 -t __NEW__ image-source
docker build --platform linux/amd64 -t __OLD__ baseline
NEW_IMAGE=$(docker image inspect __NEW__ --format '{{.Id}}')
OLD_IMAGE=$(docker image inspect __OLD__ --format '{{.Id}}')
printf '%s\n%s\n' "$NEW_IMAGE" "$OLD_IMAGE" > image-ids.txt
docker run --rm --network none __NEW__ python -c 'import sys,django; assert sys.version_info[:3]==(3,14,8); assert django.get_version()=="5.2.18"'
docker run --rm --network none __NEW__ pip check
python3 prepare.py
export SECURITY_IMAGE=__INITIAL__
dc config --quiet
STARTED=1
dc up -d --wait postgres
dc run --rm -T bootstrap
dc up -d controller
dc exec -T controller timeout 180 python -m tools.financial_rehearsal configure
dc exec -T controller python -m tools.financial_runtime_limits
__UPGRADE__
dc run --rm -T bootstrap python -m tools.financial_rehearsal test_database
dc exec -T controller python -m tools.financial_test_runner
__SCENARIO__
dc up -d --wait web
dc exec -T web python -m tools.verify_financial_web_runtime
dc exec -T web python -m tools.patch_network_probe
# Dump/restore only the synthetic database, inside the freshly generated cluster.
dc exec -T postgres timeout 600 sh -ec 'umask 077; test ! -e /backups/patch.dump; export PGPASSWORD="$(cat /run/secrets/db_bootstrap_password)"; pg_dump -h 127.0.0.1 -U mw_beta_bootstrap -d mw_beta -Fc -f /backups/patch.dump'
dc exec -T postgres timeout 600 sh -ec 'export PGPASSWORD="$(cat /run/secrets/db_bootstrap_password)"; psql -X -v ON_ERROR_STOP=1 -h 127.0.0.1 -U mw_beta_bootstrap -d mw_beta -c "CREATE DATABASE __RESTORE__ OWNER mw_beta_migrator" -c "REVOKE ALL ON DATABASE __RESTORE__ FROM PUBLIC"; pg_restore --exit-on-error -h 127.0.0.1 -U mw_beta_bootstrap -d __RESTORE__ /backups/patch.dump'
dc exec -T controller timeout 600 python -m tools.financial_restore_check
dc stop web controller postgres
echo 'Isolated checks passed. Resources retained. This is NOT a deployment.'
'''

NETWORK = r'''import socket
from tools.financial_rehearsal import marker,expect
marker()
# A successful TCP connect is a failure even if HTTP/SMTP would later reject it.
for host,port in [('1.1.1.1',443),('8.8.8.8',53)]:
 try:
  s=socket.create_connection((host,port),timeout=2)
 except OSError:
  continue
 else:
  s.close(); raise SystemExit('External egress unexpectedly available')
print('External TCP egress negative probes: PASS')
'''

AUTH = r'''"""Additional HTTP lifecycle using the scenario's real restricted LOGIN.
Only locmem and example.invalid. Credentials remain in memory.
"""
def run(case):
 import json,secrets
 from django.conf import settings
 from django.core import mail
 from django.db import connection
 from django.test import Client
 from tools.financial_rehearsal import expect
 expect(settings.ACCOUNT_SECURITY_ENABLED and settings.ACCESS_CONTROL_ENABLED and settings.ISOLATION_ENABLED)
 expect(settings.EMAIL_BACKEND=='django.core.mail.backends.locmem.EmailBackend')
 with connection.cursor() as c:
  c.execute('SELECT session_user,current_user');expect(c.fetchone()==('mw_beta_web','mw_beta_web'))
 values={'organization_id':str(case.a.pk),'username':'synthetic-patch-invite','email':'patch@example.invalid','role':'observer'}
 expect(case.post('/auth/invitations',values,csrf=False).status_code==403)
 expect(case.post('/auth/invitations',{**values,'organization_id':str(case.b.pk)}).status_code==403)
 r=case.post('/auth/invitations',values);expect(r.status_code==201)
 invite_id=r.json()['invitation_id'];old=json.loads(mail.outbox[-1].body)['token']
 expect(case.post('/auth/invitations/'+invite_id+'/reinvite').status_code==201)
 token=json.loads(mail.outbox[-1].body)['token']
 guest=Client(enforce_csrf_checks=True);password=secrets.token_urlsafe(24)
 payload={'token':old,'new_password1':password,'new_password2':password}
 expect(case.post('/auth/invitations/accept',payload,guest).status_code==400)
 payload['token']=token
 expect(case.post('/auth/invitations/accept',payload,guest).status_code==200)
 expect(case.post('/auth/invitations/accept',payload,guest).status_code==400)
 guest.get('/auth/mfa/login/',secure=True)
 expect(case.post('/auth/mfa/login/',{'personal_login-current_step':'auth','auth-username':values['username'],'auth-password':password},guest).status_code==302)
 expect(guest.get('/auth/session',secure=True).status_code==200)
 expect(guest.get(case.url(),secure=True).status_code==403) # invitation grants no business access
 expect(case.post('/auth/logout',client=guest,csrf=False).status_code==403)
 expect(case.post('/auth/logout',client=guest).status_code==200)
 expect(guest.get('/auth/session',secure=True).status_code==401)
 expect(case.post('/auth/recovery/request',{'username':values['username']},guest).status_code==202)
 reset=json.loads(mail.outbox[-1].body);password=secrets.token_urlsafe(24)
 reset.update(new_password1=password,new_password2=password)
 expect(case.post('/auth/recovery/confirm',reset,guest).status_code==200)
 expect(case.post('/auth/recovery/confirm',reset,guest).status_code==400)
 expect(all(set(m.to)=={'patch@example.invalid'} for m in mail.outbox))
 print('Restricted LOGIN: invitations/reinvite/accept/recovery/logout/CSRF/default-deny PASS')
'''


def render(output, run_id, mode, baseline):
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{5,45}', run_id):
        raise ValueError('Use a unique lowercase run id')
    if output.exists():
        raise ValueError('Output already exists; preserve prior run')
    project = 'mw-patch-' + run_id
    restore = 'mw_patch_' + run_id.replace('-', '_') + '_restore'
    if len(restore) > 63:
        raise ValueError('Restore database identifier too long')
    output.mkdir(parents=True)
    # Explicit allowlist; do not copy venv, credentials, caches or untracked files.
    import subprocess
    names = subprocess.check_output(['git', 'ls-files', 'backend'], cwd=REPO, text=True).splitlines()
    for name in names:
        source = REPO / name
        if source.is_symlink() or not source.is_file():
            raise ValueError('Unexpected backend source')
        target = output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        data = source.read_bytes()
        clean = output / 'image-source' / Path(name).relative_to('backend')
        clean.parent.mkdir(parents=True, exist_ok=True)
        clean.write_bytes(data)
        if source.suffix == '.py':
            data = data.replace(OLD_PROJECT.encode(), project.encode())
            data = data.replace(b'mw_e209_01a115d9_r4_restore', restore.encode())
        if name == 'backend/tools/financial_rehearsal.py':
            anchor = b'    run_finance(case)'
            assert data.count(anchor) == 1
            data = data.replace(anchor, anchor + b'\n    from tools.patch_auth_probe import run as run_patch_auth\n    run_patch_auth(case)')
        target.write_bytes(data)
    for name, data in [('patch_upgrade_probe.py', UPGRADE), ('patch_network_probe.py', NETWORK), ('patch_auth_probe.py', AUTH)]:
        (output / 'backend/tools' / name).write_text(data, encoding='utf-8', newline='\n')
    shutil.copytree(output / 'image-source', output / 'baseline')
    for name in ['Dockerfile', 'requirements.lock', 'requirements.in']:
        shutil.copy2(baseline / 'backend' / name, output / 'baseline' / name)
    cfg = json.loads((REPO / 'beta/deploy/compose.financial-rehearsal.json').read_text())
    text = json.dumps(cfg).replace(OLD_PROJECT, project).replace(OLD_ROOT, '.')
    text = text.replace('${SECURITY_SOURCE:?published detached Git backend required}', './backend')
    cfg = json.loads(text)
    pg = json.loads((REPO / 'beta/deploy/images.lock.json').read_text())['postgres']
    cfg['services']['postgres']['image'] = pg
    for service in cfg['services'].values():
        service['platform'] = 'linux/amd64'
        if service is not cfg['services']['postgres']:
            service['image'] = '${SECURITY_IMAGE:?explicit patch image required}'
    cfg['services']['web']['healthcheck'] = {
        'test': ['CMD', 'python', '-c', "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health/ready',timeout=3)"],
        'interval': '3s', 'timeout': '5s', 'retries': 20,
    }
    assert cfg['networks']['private']['internal'] is True
    assert all(not s.get('ports') and s['restart'] == 'no' for s in cfg['services'].values())
    (output / 'compose.json').write_text(json.dumps(cfg, indent=2) + '\n')
    (output / 'prepare.py').write_text(PREPARE, newline='\n')
    new = 'marketplace-workspace/backend:patch-3148-5218-' + run_id
    old = 'marketplace-workspace/backend:baseline-3147-5217-' + run_id
    upgrade = '''dc exec -T controller python -m tools.financial_rehearsal scenario
dc exec -T controller python -m tools.patch_upgrade_probe before
dc stop controller
export SECURITY_IMAGE="$NEW_IMAGE"
dc up -d --no-deps controller
dc exec -T controller python -m tools.patch_upgrade_probe after'''
    run = RUN.replace('__PG__', pg).replace('__OLD__', old).replace('__RESTORE__', restore)
    run = run.replace('__INITIAL__', '"$OLD_IMAGE"' if mode == 'upgrade' else '"$NEW_IMAGE"')
    run = run.replace('__UPGRADE__', upgrade if mode == 'upgrade' else '')
    run = run.replace('__SCENARIO__', '' if mode == 'upgrade' else 'dc exec -T controller python -m tools.financial_rehearsal scenario')
    (output / 'run.sh').write_text(run.replace('__NEW__', new), newline='\n')
    manifest = {str(p.relative_to(output)).replace('\\', '/'): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(output.rglob('*')) if p.is_file()}
    (output / 'source-manifest.json').write_text(json.dumps(manifest, indent=2))
    print(json.dumps({'kit': str(output), 'project': project, 'mode': mode, 'files': len(manifest), 'executed': False}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--mode', choices=['fresh', 'upgrade'], required=True)
    parser.add_argument('--baseline-backup', type=Path, required=True)
    args = parser.parse_args()
    render(args.output.resolve(), args.run_id, args.mode, args.baseline_backup.resolve())
