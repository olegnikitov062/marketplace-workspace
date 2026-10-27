"""Build a source-only archive; never include runtime data or secrets."""
from pathlib import Path
import json,hashlib,tarfile,io,ast
ROOT=Path(__file__).resolve().parent.parent
entries=[]
for directory,target in [("backend","app/backend"),("frontend","app/frontend"),("beta/deploy","deploy")]:
    for p in (ROOT/directory).rglob("*"):
        if not p.is_file():continue
        rel=p.relative_to(ROOT/directory)
        if any(part in {".venv","node_modules","__pycache__","dist"} for part in rel.parts):continue
        if p.suffix in {".pyc",".tar"} or p.name in {"source-manifest.json","bundle.tar"}:continue
        if directory=="beta/deploy" and p.name not in {"compose.json","images.lock.json","beta.py","reproduce.py","verify_migrations.py","verify_isolation.py"}:continue
        if p.suffix == ".py": ast.parse(p.read_text(encoding="utf-8"), filename=str(p))
        entries.append((target+"/"+rel.as_posix(),p.read_bytes()))
entries.sort()
manifest_files=[{"path":name,"sha256":hashlib.sha256(content).hexdigest()} for name,content in entries]
release="e2-03-"+hashlib.sha256(json.dumps(manifest_files,sort_keys=True).encode()).hexdigest()[:12]
manifest=json.dumps({"release":release,"files":manifest_files},indent=2).encode()+b"\n"
output=ROOT/"artifacts";output.mkdir(exist_ok=True)
archive=output/(release+".tar")
if archive.exists():raise SystemExit("Archive already exists; do not overwrite")
with tarfile.open(archive,"w") as tar:
    for name,content in entries+[("deploy/source-manifest.json",manifest)]:
        info=tarfile.TarInfo(name);info.size=len(content);info.mode=0o644;info.mtime=0;tar.addfile(info,io.BytesIO(content))
print(json.dumps({"release":release,"archive":str(archive),"sha256":hashlib.sha256(archive.read_bytes()).hexdigest(),"files":len(entries)}))
