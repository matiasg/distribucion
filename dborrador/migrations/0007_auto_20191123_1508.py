# Generated by Django 2.1.11 on 2019-11-23 18:08

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('dborrador', '0006_auto_20190717_0021'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='comentario',
            name='turno',
        ),
        migrations.DeleteModel(
            name='Comentario',
        ),
    ]