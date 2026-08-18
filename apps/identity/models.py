from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    mobile = models.CharField(max_length=15, blank=True, unique=True, null=True)
    is_mfa_enabled = models.BooleanField(default=False)
