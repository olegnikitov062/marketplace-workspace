"""Offline local envelope tool; never reads the application's runtime settings."""
import argparse
import getpass
import os
from pathlib import Path

from account_security.key_backup import wrap, unwrap
from account_security.operator import write_private_new


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["wrap", "restore"])
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    # Linux private permissions are enforced here. Windows ACL need a reviewed
    # private destination; this tool must not pretend chmod protects a Windows file.
    if os.name == "nt":
        raise SystemExit("Windows credential output requires a separately verified private ACL destination; use the reviewed operator environment.")
    try:
        source, target = Path(args.input), Path(args.output)
        if not source.is_file() or target.exists() or target.is_symlink() or source.stat().st_size > 4096:
            raise ValueError()
        password = getpass.getpass("Separate backup passphrase: ")
        if args.action == "wrap" and password != getpass.getpass("Confirm backup passphrase: "):
            raise ValueError()
        result = wrap(source.read_bytes().strip(), password) if args.action == "wrap" else unwrap(source.read_bytes(), password)
        write_private_new(target, result)
    except Exception:
        raise SystemExit("Key backup operation failed; no values disclosed") from None
    print("Key backup operation completed; output is private and was not transferred")


if __name__ == "__main__":
    main()
