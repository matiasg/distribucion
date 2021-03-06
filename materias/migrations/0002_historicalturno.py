# Generated by Django 2.1.7 on 2019-04-21 04:46

from django.conf import settings
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import simple_history.models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('materias', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='HistoricalTurno',
            fields=[
                ('id', models.IntegerField(auto_created=True, blank=True, db_index=True, verbose_name='ID')),
                ('anno', models.IntegerField()),
                ('cuatrimestre', models.CharField(choices=[('P', '1'), ('S', '2'), ('V', 'V')], max_length=1)),
                ('numero', models.IntegerField()),
                ('subnumero', models.CharField(blank=True, max_length=6)),
                ('tipo', models.CharField(choices=[('T', 'Teórica'), ('P', 'Práctica'), ('A', 'Teórico-Práctica')], max_length=1)),
                ('necesidad_prof', models.PositiveIntegerField(validators=[django.core.validators.MaxValueValidator(15)])),
                ('necesidad_jtp', models.PositiveIntegerField(validators=[django.core.validators.MaxValueValidator(15)])),
                ('necesidad_ay1', models.PositiveIntegerField(validators=[django.core.validators.MaxValueValidator(15)])),
                ('necesidad_ay2', models.PositiveIntegerField(validators=[django.core.validators.MaxValueValidator(15)])),
                ('history_id', models.AutoField(primary_key=True, serialize=False)),
                ('history_date', models.DateTimeField()),
                ('history_change_reason', models.CharField(max_length=100, null=True)),
                ('history_type', models.CharField(choices=[('+', 'Created'), ('~', 'Changed'), ('-', 'Deleted')], max_length=1)),
                ('history_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('materia', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='materias.Materia')),
            ],
            options={
                'verbose_name': 'historical turno',
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': 'history_date',
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
    ]
