"""Synthetic in-memory checks only; inherited argv guard forbids serving this config."""
from .accounts_local_checks import *  # noqa: F403
from account_security.configuration import configure

configure(globals(), offline=True)
SECURITY_DOWNLOAD_PROBE = True
