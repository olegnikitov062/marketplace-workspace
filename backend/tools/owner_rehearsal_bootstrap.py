"""Bootstrap only the NEW synthetic E2-06 cluster, never the primary beta."""
import json
import os
import runpy
from pathlib import Path

import psycopg

from tools.owner_rehearsal import PROJECT, PROJECTS, ROOT, expect


def main():
    try:
        expect(PROJECT in PROJECTS)
        expect(os.environ.get("E206_REHEARSAL") == PROJECT and os.environ.get("ENVIRONMENT") == "beta")
        expect(os.environ.get("TARGET_TEST", "false") == "false")
        expect(json.loads((ROOT / "manifest.json").read_text()) == {"project": PROJECT, "synthetic_only": True})
        password = Path("/run/secrets/db_bootstrap_password").read_text().strip()
        with psycopg.connect(host="postgres", dbname="mw_beta", user="mw_beta_bootstrap", password=password, connect_timeout=5) as conn:
            expect(conn.execute("SELECT current_database(),session_user,current_setting('cluster_name')").fetchone()
                   == ("mw_beta", "mw_beta_bootstrap", PROJECT))
            expect(conn.execute("SELECT count(*) FROM pg_tables WHERE schemaname='public'").fetchone() == (0,))
            expect(conn.execute("SELECT count(*) FROM pg_roles WHERE rolname IN ('mw_beta_web','mw_beta_migrator')").fetchone() == (0,))
        runpy.run_module("tools.bootstrap_roles", run_name="__main__")
    except Exception:
        raise SystemExit("Synthetic bootstrap refused; preserve state; no details disclosed") from None


if __name__ == "__main__":
    main()
