from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.contrib.contenttypes.models import ContentType

from dborrador.models import Preferencia, Asignacion


class Usuario(AbstractUser):

    pass

class Grupo(Group):

    pass


def crear_grupos_fijos():
    permisos_dborrador = Permission.objects.filter(content_type__app_label='dborrador')
    permisos_materias = Permission.objects.filter(content_type__app_label='materias')
    permiso_ver_encuestas = Permission.objects.filter(content_type__app_label='encuestas',
                                                      codename__startswith='view')

    secretaries, _ = Grupo.objects.get_or_create(name='Secretaries')
    secretaries.permissions.add(*permisos_materias)

    distribuidores, _ = Grupo.objects.get_or_create(name='Distribuidores')
    distribuidores.permissions.add(*permisos_dborrador, *permiso_ver_encuestas)
