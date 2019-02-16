from django.http import Http404, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone

from materias.models import Turno, Docente, Cargos, TurnoTipos
from .models import PreferenciasDocente

class Mapeos:
    '''Esta clase resuelve distintos tipos de mapeos'''

    @staticmethod
    def docentes(tipo):
        '''P: profesor, J: JTP y Ay1, A: Ay2'''
        el_mapa = {'P': [Cargos.Tit.name, Cargos.Aso.name, Cargos.Adj.name],
                   'J': [Cargos.JTP.name, Cargos.Ay1.name],
                   'A': [Cargos.Ay2.name],
                   }
        cargos = el_mapa[tipo.upper()]
        return Docente.objects.filter(cargo__in=cargos)

    @staticmethod
    def encuesta_tipo_turno(tipo_docente):
        '''
        Para profesores: teóricas y teórico-prácticas.
        Para auxiliares: prácticas y teórico-prácticas.
        '''
        el_mapa = {'P': [TurnoTipos.T.name, TurnoTipos.A.name],
                   'J': [TurnoTipos.P.name, TurnoTipos.A.name],
                   'A': [TurnoTipos.P.name, TurnoTipos.A.name],
                   }
        tipos = el_mapa[tipo_docente.upper()]
        return Turno.objects.filter(tipo__in=tipos)


def checkear_y_salvar(datos):
    fecha_encuesta = timezone.now()
    docente = Docente.objects.get(pk=datos['docente'])
    opciones = []
    for opcion in range(1, 6):
        turno = Turno.objects.get(pk=datos['opcion{}'.format(opcion)])
        peso = int(datos['peso{}'.format(opcion)])
        
        preferencia = PreferenciasDocente(docente=docente,
                                          turno=turno, peso=peso,
                                          anno=anno, cuatrimestre=cuatrimestre,
                                          fecha_encuesta=fecha_encuesta)
        preferencia.save()
        opciones.append((turno, peso))


def index(request):
    raise Http404('eh fiera para')


def encuesta(request, anno, cuatrimestre, tipo_docente):
    try:
        docente = Docente.objects.get(pk=request.POST['docente'])
    except (ValueError, KeyError, Turno.DoesNotExist):
        return render(request, 'encuestas/encuesta.html',
                      {'turnos': Mapeos.encuesta_tipo_turno(tipo_docente),
                       'docentes': Mapeos.docentes(tipo_docente),
                       'anno': anno,
                       'cuatrimestre': cuatrimestre,
                       'tipo_docente': tipo_docente,
                       'error_message': 'Esto esta mal, muy mal',
                        })
    else:
        checkear_y_salvar(request.POST)
        return HttpResponseRedirect(reverse('final_de_encuesta'))  # TODO: mandar las preferencias


def final(request):
    return render(request, 'encuestas/final.html')
