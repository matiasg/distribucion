# Generated by Django 2.1.7 on 2019-04-21 04:55

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import simple_history.models


class Migration(migrations.Migration):

    dependencies = [
        ('materias', '0003_historicalcarga'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('encuestas', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='HistoricalPreferenciasDocente',
            fields=[
                ('id', models.IntegerField(auto_created=True, blank=True, db_index=True, verbose_name='ID')),
                ('cargo', models.CharField(choices=[('Tit', 'Prof. Titular'), ('Aso', 'Prof. Asociado'), ('Adj', 'Prof. Adjunto'), ('JTP', 'Jefe de Trabajos Prácticos'), ('Ay1', 'Ayudante de 1ra'), ('Ay2', 'Ayudante de 2da')], max_length=3)),
                ('peso', models.FloatField(null=True)),
                ('fecha_encuesta', models.DateTimeField()),
                ('history_id', models.AutoField(primary_key=True, serialize=False)),
                ('history_date', models.DateTimeField()),
                ('history_change_reason', models.CharField(max_length=100, null=True)),
                ('history_type', models.CharField(choices=[('+', 'Created'), ('~', 'Changed'), ('-', 'Deleted')], max_length=1)),
                ('docente', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='materias.Docente')),
                ('history_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('turno', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='materias.Turno')),
            ],
            options={
                'verbose_name': 'historical preferencias docente',
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': 'history_date',
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
    ]
