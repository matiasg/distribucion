from django.db import models
from django.contrib.auth.models import AbstractUser, Group

class Usuario(AbstractUser):

    puede_distribuir = models.BooleanField('puede distribuir',
                                           default=False)
