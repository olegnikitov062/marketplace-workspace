"""Закреплённый HTTPS origin и доверие только известному gateway стенда."""
import ipaddress
import json
from pathlib import Path

from django.conf import settings
from django.core.exceptions import DisallowedHost
from django.http import JsonResponse
from django.utils.cache import patch_cache_control

from .oidc_configuration import https_url, unique_object

CONFIG = '/run/config/basework_public.json'


def address(value):
    if not isinstance(value, str) or '%' in value:
        raise ValueError()
    ip = ipaddress.ip_address(value)
    if str(ip) != value or ip.is_unspecified or ip.is_multicast:
        raise ValueError()
    return value


def parse(raw):
    if len(raw) > 8192:
        raise ValueError()
    value = json.loads(raw, object_pairs_hook=unique_object)
    if not isinstance(value, dict) or set(value) != {'origin', 'trusted_proxy_ips'}:
        raise ValueError()
    url = https_url(value['origin'])
    if url.path or url.port == 443:
        raise ValueError()
    peers = value['trusted_proxy_ips']
    if not isinstance(peers, list) or not 1 <= len(peers) <= 4:
        raise ValueError()
    peers = [address(ip) for ip in peers]
    if len(set(peers)) != len(peers):
        raise ValueError()
    return {'origin': value['origin'], 'host': url.hostname, 'authority': url.netloc,
            'trusted_proxy_ips': tuple(peers)}


def load(env):
    if env.get('BASEWORK_PUBLIC_CONFIG_FILE') != CONFIG:
        raise ValueError()
    path = Path(CONFIG)
    if path.is_symlink() or not path.is_file():
        raise ValueError()
    return parse(path.read_bytes())


class TrustedGateway:
    """Выполняется до сессий, определения secure и SQL boundary."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        config = settings.BASEWORK_PUBLIC
        try:
            peer = address(request.META.get('REMOTE_ADDR'))
            if peer not in config['trusted_proxy_ips']:
                raise ValueError()
            if request.META.get('HTTP_X_FORWARDED_PROTO') != 'https':
                raise ValueError()
            if request.get_host() != config['authority']:
                raise ValueError()
            if request.META.get('HTTP_X_FORWARDED_HOST', config['authority']) != config['authority']:
                raise ValueError()
            client = address(request.META.get('HTTP_X_BASEWORK_CLIENT_IP'))
        except (ValueError, DisallowedHost):
            response = JsonResponse({'status': 'denied'}, status=403)
            patch_cache_control(response, private=True, no_store=True)
            return response
        # Используем только отдельный заголовок, перезаписанный известным peer.
        request.META['REMOTE_ADDR'] = client
        request.META.pop('HTTP_X_FORWARDED_FOR', None)
        request.META.pop('HTTP_FORWARDED', None)
        # Старый ACL-путь download обходит SECURITY_DOWNLOAD_PROBE.
        if request.path == '/auth/security/probe' or request.path.startswith('/auth/security/probe/'):
            response = JsonResponse({'status': 'not_found'}, status=404)
            patch_cache_control(response, private=True, no_store=True)
            return response
        return self.get_response(request)
