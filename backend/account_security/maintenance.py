"""Fail-closed rollback entrypoint: stdlib only, no Django, DB or MFA bypass."""


def application(environ, start_response):
    live = environ.get("PATH_INFO") == "/api/v1/health/live"
    body = b'{"status":"maintenance"}'
    start_response("200 OK" if live else "503 Service Unavailable", [
        ("Content-Type", "application/json"), ("Cache-Control", "no-store"),
        ("Content-Length", str(len(body))), ("Retry-After", "300"),
    ])
    return [body]
