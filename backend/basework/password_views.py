"""Страница BaseWork поверх существующего входа и реестра сессий."""
from django import forms
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters, sensitive_variables
from django.views.decorators.http import require_http_methods

from account_security.forms import PasswordForm, TokenForm
from account_security.views import PersonalLogin
from accounts.limits import allow_attempt
from .personal_access import use_code


class BaseWorkPasswordForm(PasswordForm):
    error_messages = {
        **PasswordForm.error_messages,
        'invalid_login': 'Неверный логин или пароль.',
        'inactive': 'Вход в этот аккаунт недоступен.',
    }

    def __init__(self, request=None, *args, **kwargs):
        super().__init__(request, *args, **kwargs)
        for name, label in [('username', 'Логин'), ('password', 'Пароль')]:
            self.fields[name].label = label
            self.fields[name].error_messages['required'] = 'Заполните это поле.'
        self.fields['username'].widget.attrs['autocomplete'] = 'username'
        self.fields['password'].widget.attrs['autocomplete'] = 'current-password'


class BaseWorkTokenForm(TokenForm):
    def __init__(self, user, initial_device=None, request=None, *args, **kwargs):
        super().__init__(user, initial_device=initial_device, request=request, *args, **kwargs)
        self.fields['otp_token'].label = 'Код из приложения'
        self.fields['otp_token'].widget.attrs.update({
            'autocomplete': 'one-time-code', 'inputmode': 'numeric', 'autofocus': True,
        })


class BaseWorkLogin(PersonalLogin):
    template_name = 'basework/login.html'
    form_list = (('auth', BaseWorkPasswordForm), ('token', BaseWorkTokenForm))

    @sensitive_variables()
    def done(self, form_list, **kwargs):
        response = super().done(form_list, **kwargs)
        # Настройка обязательного второго фактора остаётся на прежнем маршруте.
        if response['Location'] == '/auth/security/':
            response['Location'] = '/basework/'
        return response


class PersonalAccessForm(forms.Form):
    code = forms.CharField(label='Код доступа', max_length=512,
                           widget=forms.PasswordInput(attrs={'autocomplete': 'off', 'autofocus': True}))
    new_password1 = forms.CharField(label='Новый пароль', max_length=512, strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
        help_text='Не используйте пароль от другого сервиса или только цифры.')
    new_password2 = forms.CharField(label='Повторите пароль', max_length=512, strip=False,
                                    widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.error_messages.update(required='Заполните это поле.', max_length='Значение слишком длинное.')


@never_cache
@sensitive_post_parameters()
@require_http_methods(['GET', 'POST'])
@csrf_protect
@sensitive_variables()
def personal_access(request):
    form = PersonalAccessForm(request.POST if request.method == 'POST' else None)
    status, completed, username = 200, False, None
    if not request.is_secure():
        return render(request, 'basework/access.html', {'form': form}, status=403)
    if request.method == 'POST':
        if not allow_attempt('basework_personal_access', request.META.get('REMOTE_ADDR', '')):
            form.add_error(None, 'Слишком много попыток. Попробуйте позже.')
            status = 429
        elif (request.content_type != 'application/x-www-form-urlencoded'
              or set(request.POST) - {'csrfmiddlewaretoken'} != set(form.fields)
              or any(len(request.POST.getlist(key)) != 1 for key in form.fields)):
            form.add_error(None, 'Проверьте поля формы.')
            status = 400
        elif form.is_valid():
            try:
                username = use_code(form.cleaned_data['code'], form.cleaned_data['new_password1'], form.cleaned_data['new_password2'])
                completed = True
            except PermissionDenied:
                form.add_error(None, 'Код недействителен, уже использован или истёк. Запросите новый код у администратора.')
                status = 400
            except ValidationError as error:
                for field, errors in error.error_dict.items():
                    for value in errors:
                        form.add_error(field if field in form.fields else None, value)
                status = 400
        else:
            status = 400
    return render(request, 'basework/access.html', {'form': form, 'completed': completed, 'username': username}, status=status)
