# Generated by Django 2.1.7 on 2019-04-20 15:38

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('materias', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='PreferenciasDocente',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cargo', models.CharField(choices=[('Tit', 'Prof. Titular'), ('Aso', 'Prof. Asociado'), ('Adj', 'Prof. Adjunto'), ('JTP', 'Jefe de Trabajos Prácticos'), ('Ay1', 'Ayudante de 1ra'), ('Ay2', 'Ayudante de 2da')], max_length=3)),
                ('peso', models.FloatField(null=True)),
                ('fecha_encuesta', models.DateTimeField()),
                ('docente', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='materias.Docente')),
                ('turno', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='materias.Turno')),
            ],
        ),
    ]
