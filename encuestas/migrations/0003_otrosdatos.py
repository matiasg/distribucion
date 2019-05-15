# Generated by Django 2.1.7 on 2019-05-12 14:08

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('materias', '0007_auto_20190504_1552'),
        ('encuestas', '0002_historicalpreferenciasdocente'),
    ]

    operations = [
        migrations.CreateModel(
            name='OtrosDatos',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fecha_encuesta', models.DateTimeField()),
                ('comentario', models.TextField()),
                ('cargas', models.PositiveIntegerField(validators=[django.core.validators.MaxValueValidator(3)])),
                ('email', models.EmailField(max_length=254)),
                ('telefono', models.CharField(blank=True, max_length=17, validators=[django.core.validators.RegexValidator(message='El teléfono debe contener +, números, espacios, -.', regex='^\\+?[0-9 -]{9,15}$')])),
                ('docente', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='materias.Docente')),
            ],
        ),
    ]
