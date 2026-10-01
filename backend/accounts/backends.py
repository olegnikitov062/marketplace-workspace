from django.contrib.auth.backends import ModelBackend
from .models import AccountContact


class PersonalAccountBackend(ModelBackend):
    def user_can_authenticate(self, user):
        return (super().user_can_authenticate(user) and user.archived_at is None
                and not AccountContact.objects.filter(user=user, activated_at__isnull=True).exists())
