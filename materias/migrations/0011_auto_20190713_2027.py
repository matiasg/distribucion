# Generated by Django 2.1.10 on 2019-07-13 23:27

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('materias', '0010_auto_20190630_1940'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='docente',
            options={'ordering': ['na_apellido', 'na_nombre']},
        ),
    ]
