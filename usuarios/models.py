import logging

from django.db import models
from django.contrib import admin
from django.contrib.auth.models import User, BaseUserManager, AbstractUser, Group, Permission
from django.contrib.contenttypes.models import ContentType

from dborrador.models import Preferencia, Asignacion


class UsuarioManager(BaseUserManager):

    def create_user(self, username, password=None, **kwargs):
        usuario = self.model(username=username, **kwargs)
        usuario.set_password(password)
        usuario.save()
        return usuario

    def create_superuser(self, username, password=None, **kwargs):
        usuario = self.create_user(username, password, **kwargs)
        usuario.is_superuser = True
        usuario.save()
        return usuario


class Usuario(AbstractUser):

    is_staff = models.BooleanField(default=True)
    objects = UsuarioManager()


class Grupo(Group):

    pass


def crear_grupos_fijos():
    permisos_dborrador = Permission.objects.filter(content_type__app_label='dborrador')
    permisos_materias = Permission.objects.filter(content_type__app_label='materias')
    permisos_ver_materias = Permission.objects.filter(content_type__app_label='materias',
                                                      codename__startswith='view')
    permiso_ver_encuestas = Permission.objects.filter(content_type__app_label='encuestas',
                                                      codename__startswith='view')

    secretaries, _ = Grupo.objects.get_or_create(name='Secretaries')
    secretaries.permissions.add(*permisos_materias)

    distribuidores, _ = Grupo.objects.get_or_create(name='Distribuidores')
    distribuidores.permissions.add(*permisos_dborrador, *permiso_ver_encuestas, *permisos_ver_materias)
