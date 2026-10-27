"""Локальный OIDC-вход; существующие прикладные права и MFA не назначаются здесь."""
from functools import wraps
from django import forms
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db import DatabaseError
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_GET, require_http_methods
from accounts.limits import allow_attempt
from . import oidc


def guarded(view):
    @wraps(view)
    def wrapped(request):
        if not getattr(settings, 'BASEWORK_OIDC_ENABLED', False):
            return JsonResponse({'status': 'oidc_unavailable'}, status=503)
        if not request.is_secure():
            return JsonResponse({'status': 'denied'}, status=403)
        try:
            oidc.enabled()
            return view(request)
        except PermissionDenied:
            return JsonResponse({'status': 'denied'}, status=403)
        except DatabaseError:
            return JsonResponse({'status': 'access_unavailable'}, status=503)
    return wrapped


class FactorForm(forms.Form):
    token = forms.RegexField(r'^\d{6}$', max_length=6, label='Код приложения-аутентификатора',
                            widget=forms.TextInput(attrs={'autocomplete': 'one-time-code', 'inputmode': 'numeric'}))


@require_http_methods(['GET', 'POST'])
@csrf_protect
@guarded
def login(request):
    if request.method == 'GET':
        return render(request, 'basework/oidc.html', {'title': 'Вход в BaseWork', 'button': 'Продолжить общий вход'})
    url, cookie = oidc.begin(request)
    response = redirect(url)
    response.set_cookie(oidc.COOKIE, cookie, max_age=300, secure=True, httponly=True, samesite='Lax', path='/')
    return response


def outcome(result):
    if result == 'complete':
        response = redirect('/basework/profile')
        response.delete_cookie(oidc.COOKIE, path='/', samesite='Lax')
        return response
    if result == 'setup_required':
        return JsonResponse({'status': 'local_mfa_setup_required'}, status=403)
    return redirect('/auth/basework/oidc/mfa')


@require_GET
@guarded
def callback(request):
    return outcome(oidc.callback(request))


@require_http_methods(['GET', 'POST'])
@sensitive_post_parameters()
@csrf_protect
@guarded
def mfa(request):
    attempt = oidc.pending(request)
    if attempt is None:
        raise PermissionDenied()
    form = FactorForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST':
        if not allow_attempt('oidc_mfa', request.META.get('REMOTE_ADDR', ''), str(attempt.binding_id)):
            raise PermissionDenied()
        if form.is_valid():
            result = oidc.finish(request, attempt, form.cleaned_data['token'])
            if result != 'invalid_factor':
                return outcome(result)
            form.add_error('token', 'Код не принят.')
    return render(request, 'basework/oidc.html', {'title': 'Подтверждение MFA BaseWork',
                  'button': 'Подтвердить', 'form': form}, status=400 if request.method == 'POST' else 200)
