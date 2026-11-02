"""Управление личными пользователями, только с подтверждённой сессией администратора."""
from functools import wraps
from datetime import timedelta
from zoneinfo import ZoneInfo

from django import forms
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db import DatabaseError, IntegrityError
from django.http import Http404
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters, sensitive_variables
from django.views.decorators.http import require_http_methods

from account_security import services as security
from accounts.limits import allow_attempt
from ownership.models import User
from . import user_admin as service
from .models import Administrator, ApplicationAccess

ROOT = '/auth/basework/users/'


class RussianForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.error_messages.update(required='Заполните это поле.', invalid_choice='Выберите допустимый раздел.',
                                        max_length='Значение слишком длинное.')


class AccessForm(RussianForm):
    version = forms.IntegerField(min_value=1, widget=forms.HiddenInput)
    applications = forms.MultipleChoiceField(label='Доступные разделы', choices=service.CHOICES,
                                             required=False, widget=forms.CheckboxSelectMultiple)


class CreateForm(RussianForm):
    ticket = forms.CharField(max_length=512, widget=forms.HiddenInput)
    username = forms.RegexField(r'^[a-z][a-z0-9._-]{2,63}$', label='Логин', max_length=64,
        help_text='От 3 до 64 символов: латинские строчные буквы, цифры, точка, дефис и подчёркивание. Логин задаётся при создании.',
        error_messages={'invalid': 'Используйте строчные латинские буквы, цифры, точку, дефис или подчёркивание; начните с буквы.'},
        widget=forms.TextInput(attrs={'autocomplete': 'off', 'autofocus': True}))
    applications = forms.MultipleChoiceField(label='Доступные разделы', choices=service.CHOICES,
                                             required=False, widget=forms.CheckboxSelectMultiple)

    def clean_username(self):
        value = self.cleaned_data['username']
        if value.startswith('basework-uat-') or 'synthetic' in value:
            raise forms.ValidationError('Этот логин зарезервирован для служебных проверок.')
        return value


def page_guard(view):
    @never_cache
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        try:
            if not request.is_secure():
                raise PermissionDenied()
            if not request.user.is_authenticated:
                return render(request, 'basework/users.html', {'error': 'Войдите в BaseWork, чтобы продолжить.'}, status=401)
            service.authorize(request.user)
            return view(request, *args, **kwargs)
        except service.ConfirmationRequired:
            return render(request, 'basework/users.html', {'confirmation_required': True}, status=403)
        except PermissionDenied:
            return render(request, 'basework/users.html', {'error': 'Нет доступа к управлению пользователями BaseWork.'}, status=403)
        except (User.DoesNotExist, Http404):
            return render(request, 'basework/users.html', {'error': 'Пользователь не найден.'}, status=404)
        except DatabaseError:
            return render(request, 'basework/users.html', {'error': 'Сервис не подтвердил результат. Откройте список пользователей и проверьте состояние перед повтором.'}, status=503)
    return wrapped


def valid_post(request, form, extra=()):
    allowed = set(form.fields) | {'csrfmiddlewaretoken'} | set(extra)
    return (request.content_type == 'application/x-www-form-urlencoded'
            and not set(request.POST) - allowed
            and all(len(request.POST.getlist(key)) <= 1 for key in allowed - {'applications'})
            and len(request.POST.getlist('applications')) == len(set(request.POST.getlist('applications'))))


@sensitive_variables()
def invitation(request, user, code):
    link = request.build_absolute_uri('/auth/basework/access')
    text = f'Вход в BaseWork\nЛогин: {user.username}\nКод доступа: {code}\nУстановить пароль: {link}\nКод действует 30 минут и используется один раз.\nПосле установки пароля входите со своим логином и паролем.'
    return render(request, 'basework/users.html', {'invitation': text, 'account': user,
        'expires_at': timezone.localtime(timezone.now() + timedelta(minutes=30), ZoneInfo('Europe/Moscow')).strftime('%H:%M')})


@require_http_methods(['GET'])
@page_guard
def users(request):
    query = request.GET.get('q', '').strip()[:64]
    queryset = service.managed_users().filter(username__icontains=query).order_by('username')
    page = Paginator(queryset, 30).get_page(request.GET.get('page'))
    rows = list(page.object_list)
    administrators = set(Administrator.objects.filter(user__in=rows, revoked_at__isnull=True).values_list('user_id', flat=True))
    access = list(ApplicationAccess.objects.filter(user__in=rows, revoked_at__isnull=True,
                   application__in=['faq', 'rooms']).values_list('user_id', 'application'))
    for user in rows:
        user.section_names = [label.split(' — ')[0] for name, label in service.CHOICES if (user.pk, name) in access]
        user.waiting = not user.has_usable_password()
        user.is_basework_admin = user.pk in administrators
    return render(request, 'basework/users.html', {'listing': True, 'rows': rows, 'page': page, 'query': query})


@require_http_methods(['GET', 'POST'])
@sensitive_post_parameters()
@csrf_protect
@page_guard
@sensitive_variables()
def create_user(request):
    form = CreateForm(request.POST if request.method == 'POST' else None,
                      initial={'ticket': service.creation_ticket(request.user)})
    status = 200
    if request.method == 'POST':
        if not valid_post(request, form):
            form.add_error(None, 'Проверьте поля формы.')
            status = 400
        elif not allow_attempt('basework_user_create', str(request.user.pk)):
            form.add_error(None, 'Слишком много операций. Попробуйте позже.')
            status = 429
        elif form.is_valid():
            try:
                user, code = service.create(request.user, **form.cleaned_data)
                return invitation(request, user, code)
            except (ValidationError, IntegrityError):
                form.add_error('username', 'Логин недоступен. Выберите другой.')
                status = 409
            except service.StaleOperation:
                form.add_error(None, 'Форма устарела или создание уже выполнено. Проверьте список пользователей; при необходимости откройте новую форму.')
                status = 409
        else:
            status = 400
    return render(request, 'basework/users.html', {'creating': True, 'form': form}, status=status)


@require_http_methods(['GET', 'POST'])
@sensitive_post_parameters()
@csrf_protect
@page_guard
@sensitive_variables()
def user_detail(request, user_id):
    user = service.managed_users().get(pk=user_id)
    protected = user.pk == request.user.pk or service.PlatformRoleAssignment.objects.filter(user=user, revoked_at__isnull=True).exists()
    state = security.state_for(user)
    selected = list(ApplicationAccess.objects.filter(user=user, revoked_at__isnull=True,
                    application__in=['faq', 'rooms']).values_list('application', flat=True))
    form = AccessForm(request.POST if request.method == 'POST' else None,
                      initial={'version': state.version, 'applications': selected})
    status = 200
    if request.method == 'POST':
        if protected:
            raise PermissionDenied()
        if not valid_post(request, form, extra=['action']) or request.POST.get('action') not in {'access', 'code'}:
            form.add_error(None, 'Проверьте поля формы.')
            status = 400
        elif not allow_attempt('basework_user_change', str(request.user.pk)):
            form.add_error(None, 'Слишком много операций. Попробуйте позже.')
            status = 429
        elif form.is_valid():
            try:
                if request.POST['action'] == 'code':
                    user, code = service.issue(request.user, user_id, form.cleaned_data['version'])
                    return invitation(request, user, code)
                service.update_access(request.user, user_id, **form.cleaned_data)
                return redirect(ROOT + str(user_id) + '/?saved=1')
            except service.StaleOperation:
                form.add_error(None, 'Состояние аккаунта уже изменилось. Обновите страницу и проверьте права перед новой операцией.')
                status = 409
        else:
            status = 400
    return render(request, 'basework/users.html', {'account': user, 'form': form, 'protected': protected,
        'saved': request.GET.get('saved') == '1', 'version': state.version,
        'waiting': not user.has_usable_password()}, status=status)
