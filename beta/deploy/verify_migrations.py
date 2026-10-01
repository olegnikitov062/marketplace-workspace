"""Synthetic data only, fixed own test cluster and restore DB names."""
from pathlib import Path
import json,subprocess,hashlib,os
ROOT=Path(__file__).resolve().parent.parent
if ROOT!=Path("/home/adm_user/marketplace-workspace/beta"):raise SystemExit("Wrong beta root")
release=json.loads((ROOT/"deploy/source-manifest.json").read_text())["release"]
env={"PATH":os.environ.get("PATH","/usr/bin:/bin"),"HOME":"/home/adm_user","BACKEND_IMAGE":"marketplace-workspace/backend:"+release}
base=["docker","compose","--project-name","marketplace-beta","--env-file","/dev/null","--project-directory",str(ROOT/"deploy"),"-f",str(ROOT/"deploy/compose.json")]
def run(args,capture=False):
    p=subprocess.run(args,env=env,text=True,capture_output=capture)
    if p.returncode:raise SystemExit(p.returncode)
    return p.stdout.strip() if capture else None

def pg(command,capture=False):
    # Credentials are consumed inside the own PG container and never printed or placed in argv.
    prefix='export PGPASSWORD="$(cat /run/secrets/db_test_bootstrap_password)"; '
    return run(base+["exec","-T","postgres-test","sh","-c",prefix+command],capture)

def query(database,sql):
    if database not in {"mw_beta_test","mw_beta_test_restore"}:raise SystemExit("Wrong database")
    return pg("psql -U mw_beta_test_bootstrap -d "+database+" -v ON_ERROR_STOP=1 -tAc '"+sql+"'",True)
backup=ROOT/"backups/test/migrations-before.dump"
if backup.exists():raise SystemExit("Backup exists; do not overwrite or repeat destructive test")
run(base+["run","--rm","test","python","manage.py","migrate","--noinput"])
query("mw_beta_test", "INSERT INTO django_content_type(app_label,model) VALUES($$e2_03_synthetic$$,$$probe$$) ON CONFLICT DO NOTHING")
pg("pg_dump -U mw_beta_test_bootstrap -d mw_beta_test --format=custom --file=/backups/migrations-before.dump")
run(base+["run","--rm","test","python","manage.py","migrate","contenttypes","0001","--noinput"])
if query("mw_beta_test","SELECT COUNT(*) FROM django_migrations WHERE app=$$contenttypes$$")!="1":raise SystemExit("Migration reverse check failed")
run(base+["run","--rm","test","python","manage.py","migrate","--noinput"])
pg("createdb -U mw_beta_test_bootstrap -O mw_beta_test_runner mw_beta_test_restore")
pg("psql -U mw_beta_test_bootstrap -d mw_beta_test -v ON_ERROR_STOP=1 -c 'REVOKE CONNECT ON DATABASE mw_beta_test_restore FROM PUBLIC; GRANT CONNECT ON DATABASE mw_beta_test_restore TO mw_beta_test_runner'")
pg("pg_restore -U mw_beta_test_bootstrap -d mw_beta_test_restore --exit-on-error /backups/migrations-before.dump")
for database in ["mw_beta_test","mw_beta_test_restore"]:
    if query(database,"SELECT COUNT(*) FROM django_migrations WHERE app=$$contenttypes$$")!="2":raise SystemExit("Migration count mismatch")
    if query(database,"SELECT COUNT(*) FROM django_content_type WHERE app_label=$$e2_03_synthetic$$ AND model=$$probe$$")!="1":raise SystemExit("Synthetic row mismatch")
report={"migration_forward_reverse_forward":True,"backup_restore_separate_test_database":True,"synthetic_row_preserved":True,"dump_path":str(backup),"backup_sha256":pg("sha256sum /backups/migrations-before.dump",True).split()[0],"restored_database":"mw_beta_test_restore","production_accessed":False}
path=ROOT/"config/migration-checks.json"
if path.exists():raise SystemExit("Report already exists")
path.write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps(report))
