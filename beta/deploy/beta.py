"""Explicit, scoped operations for beta only. No production/global prune/down actions."""
import argparse,subprocess,pathlib,json,os,secrets,datetime,hashlib
ROOT=pathlib.Path(__file__).resolve().parent.parent
EXPECTED=pathlib.Path("/home/adm_user/marketplace-workspace/beta")
if ROOT!=EXPECTED or ROOT.is_symlink():raise SystemExit("Run only inside the canonical beta directory")
IMAGES=json.loads((ROOT/"deploy/images.lock.json").read_text())
MANIFEST=json.loads((ROOT/"deploy/source-manifest.json").read_text())
RELEASE=MANIFEST["release"]
BACKEND="marketplace-workspace/backend:"+RELEASE
FRONTEND="marketplace-workspace/frontend:"+RELEASE
ENV={"PATH":os.environ.get("PATH","/usr/bin:/bin"),"HOME":"/home/adm_user","BACKEND_IMAGE":BACKEND,"COMPOSE_PROFILES":""}
BASE=["docker","compose","--project-name","marketplace-beta","--env-file","/dev/null","--project-directory",str(ROOT/"deploy"),"-f",str(ROOT/"deploy/compose.json")]
def call(args,capture=False,input=None):
    p=subprocess.run(args,env=ENV,cwd=ROOT,text=True,input=input,capture_output=capture)
    if p.returncode:raise SystemExit(p.returncode)
    return p.stdout if capture else None

def verify_source():
    for item in MANIFEST["files"]:
        p=ROOT/item["path"]
        if not p.resolve().is_relative_to(ROOT) or hashlib.sha256(p.read_bytes()).hexdigest()!=item["sha256"]:raise SystemExit("Source manifest mismatch")

def prepare():
    verify_source()
    state=ROOT/"config/provisioned.json"
    if state.exists():raise SystemExit("Already prepared; do not overwrite runtime credentials")
    directory=ROOT/"config/secrets";directory.mkdir(mode=0o700,exist_ok=False)
    for name in ["db_bootstrap_password","db_migrator_password","db_web_password","db_test_bootstrap_password","db_test_runner_password","django_secret_key"]:
        path=directory/name
        descriptor=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
        with os.fdopen(descriptor,"w") as f:f.write(secrets.token_urlsafe(48))
        uid=999 if name in {"db_bootstrap_password","db_test_bootstrap_password"} else 10001
        call(["sudo","-n","chown",str(uid)+":10001",str(path)])
        call(["sudo","-n","chmod","0440" if uid==999 else "0400",str(path)])
    for rel in ["data/postgres-test","backups/test","backups/database"]:(ROOT/rel).mkdir(mode=0o700,exist_ok=True)
    state.write_text(json.dumps({"time":datetime.datetime.now(datetime.timezone.utc).isoformat(),"secret_files":6,"values_not_recorded":True})+"\n")
    call(BASE+["config","--quiet"])

def build():
    verify_source()
    call(["docker","build","--build-arg","PYTHON_IMAGE="+IMAGES["python"],"-t",BACKEND,str(ROOT/"app/backend")])
    call(["docker","build","--build-arg","NODE_IMAGE="+IMAGES["node"],"-t",FRONTEND,str(ROOT/"app/frontend")])

def start():
    call(BASE+["up","-d","postgres","postgres-test"])
    for service in ["bootstrap","bootstrap-test"]:
        state=ROOT/("config/"+service+".done")
        if not state.exists():
            call(BASE+["run","--rm",service]);state.write_text(RELEASE+"\n")
    call(BASE+["run","--rm","migrate"])
    call(BASE+["up","-d","web"])

def tests():
    call(BASE+["run","--rm","test"])
    call(BASE+["run","--rm","--no-deps","web","python","-m","tools.verify_web_role"])
    call(BASE+["exec","-T","web","python","-c",'import urllib.request; print(urllib.request.urlopen("http://127.0.0.1:8000/api/v1/health/ready",timeout=5).read().decode())'])

def status():call(BASE+["ps"])

parser=argparse.ArgumentParser();parser.add_argument("action",choices=["prepare","build","start","test","status"]);args=parser.parse_args()
{"prepare":prepare,"build":build,"start":start,"test":tests,"status":status}[args.action]()
