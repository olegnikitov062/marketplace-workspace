"""Синтетический HTTPS IdP только для внутренней сети локального тестового стенда."""
import base64
import hashlib
import json
import os
import secrets
import signal
import ssl
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock
from urllib.parse import parse_qs, urlencode, urlsplit
from joserfc import jwt
from joserfc.jwk import RSAKey
from basework.oidc_configuration import load, ISOLATED
from tools.basework_postgresql_rehearsal import marker

marker()
provider = load(os.environ) if os.environ.get('BASEWORK_OIDC_MODE') == 'provider' else ISOLATED
ISSUER, CALLBACK, SECRET = provider.issuer, provider.redirect_uri, provider.secret_file
AUTHORIZE, TOKEN, JWKS, CLIENT_ID = (provider.authorization_endpoint, provider.token_endpoint,
                                  provider.jwks_uri, provider.client_id)
codes, lock = {}, Lock()
discovery_mode = 'valid'
key = RSAKey.generate_key(2048, parameters={'kid': 'synthetic'})
other_key = RSAKey.generate_key(2048, parameters={'kid': 'synthetic'})


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # В URL есть одноразовые коды; HTTP-журнал не нужен.

    def reply(self, status, data, headers=None):
        body = json.dumps(data).encode()
        self.send_response(status)
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlsplit(self.path)
        if path.path == urlsplit(provider.discovery).path:
            metadata = {'issuer': ISSUER, 'authorization_endpoint': AUTHORIZE,
                'token_endpoint': TOKEN, 'jwks_uri': JWKS, 'response_types_supported': ['code'],
                'subject_types_supported': ['public'], 'token_endpoint_auth_methods_supported': ['client_secret_basic'],
                'code_challenge_methods_supported': ['S256'], 'id_token_signing_alg_values_supported': ['RS256']}
            changes = {'issuer': {'issuer': ISSUER+'-other'}, 'token': {'token_endpoint': ISSUER+'/unexpected'},
                       'authorize': {'authorization_endpoint': ISSUER+'/unexpected'},
                       'jwks': {'jwks_uri': ISSUER+'/unexpected'}, 'pkce': {'code_challenge_methods_supported': ['plain']},
                       'algorithm': {'id_token_signing_alg_values_supported': ['HS256']},
                       'auth': {'token_endpoint_auth_methods_supported': ['none']},
                       'inline': {'jwks': {'keys': [other_key.as_dict(private=False)]},
                                  'token_endpoint_auth_method': 'none', 'verify': False, 'scope': 'offline_access'}}
            metadata.update(changes.get(discovery_mode, {}))
            if discovery_mode == 'redirect':
                return self.reply(302, {}, {'Location': ISSUER+'/unexpected'})
            return self.reply(200, metadata)
        if path.path == urlsplit(JWKS).path:
            return self.reply(200, {'keys': [key.as_dict(private=False)]})
        if path.path != urlsplit(AUTHORIZE).path:
            return self.reply(404, {})
        q = parse_qs(path.query)
        if any(len(v) != 1 for v in q.values()) or any(q.get(k) != [v] for k, v in {
                'client_id': CLIENT_ID, 'redirect_uri': CALLBACK, 'scope': 'openid',
                'response_type': 'code', 'code_challenge_method': 'S256'}.items()):
            return self.reply(400, {})
        if not all(q.get(k) for k in ('state', 'nonce', 'code_challenge')):
            return self.reply(400, {})
        if q.get('test_mode') == ['cancel']:
            return self.reply(302, {}, {'Location': CALLBACK+'?'+urlencode({'state': q['state'][0], 'error': 'access_denied'})})
        code = secrets.token_urlsafe(32)
        # Выбор синтетического сценария есть только у тестового провайдера.
        with lock:
            codes[code] = (q, time.time())
        self.reply(302, {}, {'Location': CALLBACK + '?' + urlencode({'state': q['state'][0], 'code': code, 'iss': ISSUER})})

    def do_POST(self):
        global discovery_mode, key
        if self.path == '/__test__/discovery' and int(self.headers.get('Content-Length', '0')) < 64:
            mode = self.rfile.read(int(self.headers.get('Content-Length', '0'))).decode()
            if mode not in {'valid', 'issuer', 'token', 'authorize', 'jwks', 'pkce', 'algorithm', 'auth', 'inline', 'redirect'}:
                return self.reply(400, {})
            discovery_mode = mode
            return self.reply(200, {})
        if self.path != urlsplit(TOKEN).path or int(self.headers.get('Content-Length', '0')) > 8192:
            return self.reply(400, {})
        expected = 'Basic ' + base64.b64encode((CLIENT_ID + ':' + Path(SECRET).read_text().strip()).encode()).decode()
        if not secrets.compare_digest(self.headers.get('Authorization', ''), expected):
            return self.reply(401, {'error': 'invalid_client'})
        body = parse_qs(self.rfile.read(int(self.headers.get('Content-Length', '0'))).decode())
        with lock:
            saved = codes.pop(body.get('code', [''])[0], None)
        if saved is None or time.time() - saved[1] > 60:
            return self.reply(400, {'error': 'invalid_grant'})
        q = saved[0]
        verifier = body.get('code_verifier', [''])[0]
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
        if (body.get('redirect_uri') != [CALLBACK] or body.get('grant_type') != ['authorization_code']
                or challenge != q['code_challenge'][0]):
            return self.reply(400, {'error': 'invalid_grant'})
        mode = q.get('test_mode', ['valid'])[0]
        if mode == 'rotation':
            key = RSAKey.generate_key(2048, parameters={'kid': 'rotated'})
        if mode == 'outage':
            return self.reply(503, {})
        if mode == 'redirect':
            return self.reply(307, {}, {'Location': ISSUER + '/unexpected'})
        if mode == 'timeout':
            time.sleep(4)
            return
        now = int(time.time())
        claims = {'iss': ISSUER, 'sub': q.get('test_subject', ['unknown'])[0], 'aud': CLIENT_ID,
                  'iat': now, 'exp': now+60, 'nonce': q['nonce'][0]}
        changes = {'issuer': {'iss': 'https://other.invalid'}, 'audience': {'aud': 'wrong'},
                   'nonce': {'nonce': 'wrong'}, 'expired': {'exp': now-10}, 'missing_nonce': {}}
        claims.update(changes.get(mode, {}))
        if mode == 'missing_nonce':
            claims.pop('nonce')
        token = jwt.encode({'alg': 'RS256', 'kid': key.as_dict(private=False)['kid']}, claims, other_key if mode == 'signature' else key)
        self.reply(200, {'access_token': secrets.token_urlsafe(32), 'token_type': 'Bearer', 'id_token': token})


if __name__ == '__main__':
    marker()
    def stop(signum, frame):
        raise SystemExit(0)
    signal.signal(signal.SIGTERM, stop)
    server = ThreadingHTTPServer(('0.0.0.0', 8443), Handler)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain('/run/secrets/oidc_tls_cert', '/run/secrets/oidc_tls_key')
    server.socket = context.wrap_socket(server.socket, server_side=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()
