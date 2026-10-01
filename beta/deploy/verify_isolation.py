from pathlib import Path
import subprocess,json,os
ROOT=Path(__file__).resolve().parent.parent
if ROOT!=Path("/home/adm_user/marketplace-workspace/beta"):raise SystemExit("Wrong beta root")
release=json.loads((ROOT/"deploy/source-manifest.json").read_text())["release"]
env={"PATH":os.environ.get("PATH","/usr/bin:/bin"),"HOME":"/home/adm_user","BACKEND_IMAGE":"marketplace-workspace/backend:"+release}
base=["docker","compose","--project-name","marketplace-beta","--env-file","/dev/null","--project-directory",str(ROOT/"deploy"),"-f",str(ROOT/"deploy/compose.json")]
results=[]
for key,value,expected in [("ENVIRONMENT","production","ENVIRONMENT must"),("DB_HOST","example.invalid","DB_HOST does not match"),("DB_NAME","mw_production","DB_NAME does not match"),("DB_USER","mw_beta_bootstrap","DB_USER does not match"),("REAL_MESSAGES_ENABLED","true","REAL_MESSAGES_ENABLED must be false"),("SOURCE_DATABASE_URL","postgresql://synthetic.invalid","Source, SMTP")]:
    p=subprocess.run(base+["run","--rm","--no-deps","-e",key+"="+value,"web","python","manage.py","check"],capture_output=True,text=True,env=env)
    if p.returncode==0 or expected not in p.stderr+p.stdout:raise SystemExit("Startup guard negative test failed")
    results.append({"key":key,"rejected":True})
ids=subprocess.check_output(["docker","ps","-q","--filter","label=com.docker.compose.project=marketplace-beta","--filter","label=com.docker.compose.service=postgres-test"],text=True).strip()
ip=subprocess.check_output(["docker","inspect","--format",'{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}',ids],text=True).strip()
# Target is ONLY our separate test PostgreSQL, never an existing WB/FBS database.
code='import socket; s=socket.socket(); s.settimeout(2); rc=s.connect_ex(('+repr(ip)+',5432)); assert rc != 0, "Cross-network DB connection succeeded"; print("Own test DB unreachable from beta web network")'
p=subprocess.run(base+["run","--rm","--no-deps","web","python","-c",code],capture_output=True,text=True,env=env)
if p.returncode:raise SystemExit("Cross-network test failed")
print(json.dumps({"negative_startup_checks":results,"own_test_db_network_denial":True,"working_sources_probed":False}))
