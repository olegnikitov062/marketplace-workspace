"""Страница BaseWork поверх существующего входа и реестра сессий."""
from django.views.decorators.debug import sensitive_variables

from account_security.forms import PasswordForm, TokenForm
from account_security.views import PersonalLogin


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
