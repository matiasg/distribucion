# Generated by Django 2.1.5 on 2019-01-07 23:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('materias', '0002_auto_20190107_0906'),
    ]

    operations = [
        migrations.AlterField(
            model_name='horario',
            name='dia',
            field=models.CharField(choices=[('Lu', 'Lunes'), ('Ma', 'Martes'), ('Mi', 'Miércoles'), ('Ju', 'Jueves'), ('Vi', 'Viernes')], max_length=2),
        ),
    ]
