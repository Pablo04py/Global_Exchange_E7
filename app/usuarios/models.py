from django.contrib.auth.models import AbstractUser
from django.contrib.postgres.fields import ArrayField
from django.db import models

class Usuario(AbstractUser):
    keycloak_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    roles = ArrayField(models.CharField(max_length=100), default=list, blank=True)