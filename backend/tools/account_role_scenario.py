"""Same HTTP scenario can be checked offline; SQL-role proof is PostgreSQL-only.

No credential, identity, response body, cookie or email is printed.
"""
import json
import secrets
from urllib.parse import urlencode

from django.core import mail
from django.test import Client
from django.views.decorators.debug import sensitive_variables

from accounts.services import block_account
from ownership.models import Membership, Organization, User


def expect(condition, code):
    if not condition:
        raise RuntimeError(code)


@sensitive_variables()
def seed():
    a = Organization.objects.create(name="synthetic-role-a")
    b = Organization.objects.create(name="synthetic-role-b")
    password = secrets.token_urlsafe(24)
    owner = User.objects.create_user("synthetic-role-owner", password=password)
    Membership.objects.create(user=owner, organization=a, role="owner")
    Membership.objects.create(user=owner, organization=b, role="observer")
    return {"organization": str(a.pk), "foreign": str(b.pk), "owner": owner.username, "password": password}


def post(client, path, data=None, csrf=True):
    headers = {"HTTP_ORIGIN": "https://testserver"}
    if csrf:
        headers["HTTP_X_CSRFTOKEN"] = client.get("/auth/csrf", secure=True).json()["csrfToken"]
    return client.post(path, urlencode(data or {}), content_type="application/x-www-form-urlencoded", secure=True, **headers)


@sensitive_variables()
def run(fixture, operator_block=None):
    operator_block = operator_block or block_account
    owner = Client(enforce_csrf_checks=True)
    credentials = {"username": fixture["owner"], "password": fixture["password"]}
    expect(post(owner, "/auth/login", credentials, csrf=False).status_code == 403, "csrf_missing")
    expect(post(owner, "/auth/login", {**credentials, "password": secrets.token_urlsafe(24)}).status_code == 401, "wrong_password")
    expect(post(owner, "/auth/login", credentials).status_code == 200, "owner_login")
    invitation = {"organization_id": fixture["organization"], "username": "synthetic-role-new", "email": "role-new@example.invalid", "role": "observer"}
    expect(post(owner, "/auth/invitations", {**invitation, "organization_id": fixture["foreign"]}).status_code == 403, "foreign_scope")
    response = post(owner, "/auth/invitations", invitation)
    expect(response.status_code == 201, "invite")
    identifier = response.json()["invitation_id"]
    old = json.loads(mail.outbox[-1].body)["token"]
    response = post(owner, f"/auth/invitations/{identifier}/reinvite")
    expect(response.status_code == 201, "reinvite")
    token = json.loads(mail.outbox[-1].body)["token"]
    password = secrets.token_urlsafe(24)
    confirmation = {"token": old, "new_password1": password, "new_password2": password}
    guest = Client(enforce_csrf_checks=True)
    expect(post(guest, "/auth/invitations/accept", confirmation).status_code == 400, "old_invite")
    confirmation["token"] = token
    expect(post(guest, "/auth/invitations/accept", confirmation).status_code == 200, "accept")
    expect(post(guest, "/auth/invitations/accept", confirmation).status_code == 400, "used_invite")
    expect(post(guest, "/auth/login", {"username": invitation["username"], "password": password}).status_code == 200, "personal_login")
    expect(post(guest, "/auth/recovery/request", {"username": invitation["username"]}).status_code == 202, "recovery_request")
    reset = json.loads(mail.outbox[-1].body)
    password = secrets.token_urlsafe(24)
    reset.update(new_password1=password, new_password2=password)
    expect(post(guest, "/auth/recovery/confirm", reset).status_code == 200, "recovery_confirm")
    expect(post(guest, "/auth/recovery/confirm", reset).status_code == 400, "used_recovery")
    expect(guest.get("/auth/session", secure=True).status_code == 401, "old_session")
    credentials = {"username": invitation["username"], "password": password}
    expect(post(guest, "/auth/login", credentials).status_code == 200, "new_login")
    expect(post(guest, "/auth/logout").status_code == 200, "logout")
    expect(post(guest, "/auth/login", credentials).status_code == 200, "login_before_block")
    user = User.objects.get(username=invitation["username"])
    expect(not Membership.objects.filter(user=user, organization_id=fixture["foreign"]).exists(), "membership_scope")
    operator_block(user.pk)
    expect(guest.get("/auth/session", secure=True).status_code == 401, "blocked_session")
    expect(post(guest, "/auth/login", credentials).status_code == 401, "blocked_login")
    outbox_size = len(mail.outbox)
    expect(post(guest, "/auth/recovery/request", {"username": invitation["username"]}).status_code == 202, "blocked_recovery_response")
    expect(len(mail.outbox) == outbox_size, "blocked_recovery_delivery")
    mail.outbox.clear()
