"""Owner-operated check of an encrypted backup; never writes a plaintext key."""
import argparse
import getpass
import stat
import sys
import warnings
from pathlib import Path

from account_security.key_backup import unwrap


def verify(path, password):
    """Read ciphertext once; the recovered key never leaves this function."""
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or not 0 < info.st_size <= 4096:
        raise ValueError()
    envelope = path.read_bytes()
    if len(envelope) != info.st_size:
        raise ValueError()
    unwrap(envelope, password)  # Authenticates the envelope and validates Fernet key format.


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    args = parser.parse_args()
    # Refuse pipes/logged agent invocations and any getpass fallback with echo.
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        raise SystemExit("Use an interactive owner terminal; no password was requested.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", getpass.GetPassWarning)
            password = getpass.getpass("Separate backup passphrase (hidden): ")
        verify(args.input, password)
    except Exception:
        raise SystemExit("Encrypted backup verification failed; no values disclosed.") from None
    print("Encrypted backup verified in memory; no plaintext key was written or displayed.")


if __name__ == "__main__":
    main()
