# Generated by Django 2.1.7 on 2019-04-28 18:20

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('materias', '0004_historicaldocente_historicalhorario_historicalmateria'),
    ]

    operations = [
        migrations.AddField(
            model_name='historicalturno',
            name='alumnos',
            field=models.PositiveIntegerField(default=0, validators=[django.core.validators.MaxValueValidator(1000)]),
        ),
        migrations.AddField(
            model_name='turno',
            name='alumnos',
            field=models.PositiveIntegerField(default=0, validators=[django.core.validators.MaxValueValidator(1000)]),
        ),
    ]
