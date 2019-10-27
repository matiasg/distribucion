# Generated by Django 2.1.10 on 2019-10-26 14:56

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('encuestas', '0011_auto_20191006_2252'),
    ]

    operations = [
        migrations.AlterField(
            model_name='otrosdatos',
            name='telefono',
            field=models.CharField(blank=True, max_length=17, validators=[django.core.validators.RegexValidator(message='El celular debe ser del estilo "area número" (por ejemplo, +11 1234-5678)', regex='^\\+?[0-9 -]{9,15}$')]),
        ),
    ]
