# Generated by Django 2.1.10 on 2019-07-17 03:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('materias', '0011_auto_20190713_2027'),
    ]

    operations = [
        migrations.AlterField(
            model_name='carga',
            name='cuatrimestre',
            field=models.CharField(choices=[('V', 'V'), ('P', '1'), ('S', '2')], max_length=1),
        ),
        migrations.AlterField(
            model_name='historicalcarga',
            name='cuatrimestre',
            field=models.CharField(choices=[('V', 'V'), ('P', '1'), ('S', '2')], max_length=1),
        ),
        migrations.AlterField(
            model_name='historicalturno',
            name='cuatrimestre',
            field=models.CharField(choices=[('V', 'V'), ('P', '1'), ('S', '2')], max_length=1),
        ),
        migrations.AlterField(
            model_name='turno',
            name='cuatrimestre',
            field=models.CharField(choices=[('V', 'V'), ('P', '1'), ('S', '2')], max_length=1),
        ),
    ]
