"""Минимум шесть символов только для личных аккаунтов BaseWork."""
from django.conf import settings
from django.contrib.auth import password_validation
from django.contrib.auth.forms import PasswordChangeForm, SetPasswordForm
from django.core.exceptions import ValidationError
from django.utils.translation import override


def validators_for(user):
    validators = password_validation.get_default_password_validators()
    if not getattr(settings, 'BASEWORK_ENABLED', False) or not user or not user.pk:
        return validators
    from account_security.models import SecurityEvent
    from accounts.models import AccountContact
    from ownership.models import Membership
    from .personal_access import CREATED
    if (not user.is_active or user.archived_at
            or not SecurityEvent.objects.filter(user=user, kind=CREATED).exists()
            or AccountContact.objects.filter(user=user).exists()
            or Membership.objects.filter(user=user).exists()):
        return validators
    return [password_validation.MinimumLengthValidator(min_length=6)
            if type(validator) is password_validation.MinimumLengthValidator else validator
            for validator in validators]


class PersonalPasswordValidation:
    def __init__(self, user, *args, **kwargs):
        super().__init__(user, *args, **kwargs)
        self.password_validators = validators_for(user)
        with override('ru'):
            self.fields['new_password1'].help_text = password_validation.password_validators_help_text_html(self.password_validators)

    def validate_password_for_user(self, user, password_field_name='password2'):
        password = self.cleaned_data.get(password_field_name)
        if password:
            try:
                with override('ru'):
                    password_validation.validate_password(password, user, self.password_validators)
            except ValidationError as error:
                self.add_error(password_field_name, error)


class PersonalSetPasswordForm(PersonalPasswordValidation, SetPasswordForm):
    pass


class PersonalPasswordChangeForm(PersonalPasswordValidation, PasswordChangeForm):
    pass
