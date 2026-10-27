"""Fresh ephemeral own test cluster; clean up only IDs created by this invocation."""
from pathlib import Path
import json,subprocess,time
ROOT=Path(__file__).resolve().parent.parent
if ROOT!=Path("/home/adm_user/marketplace-workspace/beta"):raise SystemExit("Wrong beta root")
images=json.loads((ROOT/"deploy/images.lock.json").read_text())
release=json.loads((ROOT/"deploy/source-manifest.json").read_text())["release"]
backend="marketplace-workspace/backend:"+release
net="marketplace-beta-reproduce-private";name="marketplace-beta-reproduce-postgres"
def run(args,capture=False):
    p=subprocess.run(args,text=True,capture_output=capture)
    if p.returncode:raise SystemExit(p.returncode)
    return p.stdout.strip() if capture else None
if run(["docker","network","ls","--filter","name=^"+net+"$","-q"],True) or run(["docker","ps","-aq","--filter","name=^"+name+"$"],True):raise SystemExit("Probe object already exists")
network_id=None;container_id=None
base=["docker","run","--rm","--network",net,"--read-only","--cap-drop","ALL","--security-opt","no-new-privileges:true","--user","10001:10001","--memory","256m","--cpus","0.25","--pids-limit","128","--tmpfs","/tmp:size=64m","--log-opt","max-size=10m","--log-opt","max-file=3"]
def secret(name):return ["--mount","type=bind,source="+str(ROOT/"config/secrets"/name)+",target=/run/secrets/"+name+",readonly"]
try:
    network_id=run(["docker","network","create","--internal","--label","io.marketplace.owner=marketplace-workspace",net],True)
    args=["docker","run","-d","--name",name,"--network",net,"--network-alias","postgres-test","--memory","384m","--cpus","0.25","--pids-limit","128","--tmpfs","/var/lib/postgresql/data:size=192m","--log-opt","max-size=10m","--log-opt","max-file=3","-e","POSTGRES_DB=mw_beta_test","-e","POSTGRES_USER=mw_beta_test_bootstrap","-e","POSTGRES_PASSWORD_FILE=/run/secrets/db_test_bootstrap_password","-e","POSTGRES_INITDB_ARGS=--auth-local=scram-sha-256 --auth-host=scram-sha-256"]+secret("db_test_bootstrap_password")+[images["postgres"]]
    container_id=run(args,True)
    for i in range(30):
        if subprocess.run(["docker","exec",container_id,"pg_isready","-U","mw_beta_test_bootstrap","-d","mw_beta_test"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0:break
        time.sleep(1)
    else:raise SystemExit("Fresh PostgreSQL did not become ready")
    run(base+["-e","ENVIRONMENT=beta","-e","TARGET_TEST=true"]+secret("db_test_bootstrap_password")+secret("db_test_runner_password")+[backend,"python","tools/bootstrap_roles.py"])
    args=base[:]
    for k,v in {"ENVIRONMENT":"beta","PROCESS_MODE":"test","DB_HOST":"postgres-test","DB_PORT":"5432","DB_NAME":"mw_beta_test","DB_USER":"mw_beta_test_runner","DB_PASSWORD_FILE":"/run/secrets/db_test_runner_password","DJANGO_SECRET_KEY_FILE":"/run/secrets/django_secret_key"}.items():args += ["-e",k+"="+v]
    run(args+secret("db_test_runner_password")+secret("django_secret_key")+[backend,"python","manage.py","test","tests","--noinput","--verbosity","1"])
    print("Fresh cluster provisioning, migrations, five tests and test database teardown passed")
finally:
    if container_id:run(["docker","rm","-f",container_id])
    if network_id:run(["docker","network","rm",network_id])
