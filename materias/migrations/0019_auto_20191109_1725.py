# Generated by Django 2.1.10 on 2019-11-09 20:25

from django.db import migrations


def simple_a_parcial(apps, schema_editor):
    Carga = apps.get_model('materias', 'Carga')
    for carga in Carga.objects.all():
        if carga.cargo.endswith('Sim'):
            carga.cargo = carga.cargo[:3] + 'Par'
            carga.save()

    Docente = apps.get_model('materias', 'Docente')
    for docente in Docente.objects.all():
        docente.cargos = [c.replace('Sim', 'Par') for c in docente.cargos]
        docente.save()

    HCarga = apps.get_model('materias', 'HistoricalCarga')
    for hcarga in HCarga.objects.all():
        if hcarga.cargo.endswith('Sim'):
            hcarga.cargo = hcarga.cargo[:3] + 'Par'
            hcarga.save()

    HDocente = apps.get_model('materias', 'HistoricalDocente')
    for hdocente in HDocente.objects.all():
        hdocente.cargos = [c.replace('Sim', 'Par') for c in hdocente.cargos]
        hdocente.save()


class Migration(migrations.Migration):

    dependencies = [
        ('materias', '0018_auto_20191109_1714'),
    ]

    operations = [
        migrations.RunPython(simple_a_parcial),
    ]
