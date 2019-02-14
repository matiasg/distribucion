from django.http import Http404, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone

from materias.models import Turno, Docente, Mapeos
from .models import PreferenciasDocente

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
        fecha_encuesta = timezone.now()
        docente = Docente.objects.get(pk=request.POST['docente'])
        opciones = []
        for opcion in range(1, 6):
            turno = Turno.objects.get(pk=request.POST['opcion{}'.format(opcion)])
            peso = int(request.POST['peso{}'.format(opcion)])
            
            preferencia = PreferenciasDocente(docente=docente,
                                              turno=turno, peso=peso,
                                              anno=anno, cuatrimestre=cuatrimestre,
                                              fecha_encuesta=fecha_encuesta)
            preferencia.save()
            opciones.append((turno, peso))

        return HttpResponseRedirect(reverse('final_de_encuesta'))  # TODO: mandar las preferencias

def final(request):
    return render(request, 'encuestas/final.html')
