from django.http import Http404, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse

from materias.models import Turno, Docente

def index(request):
    raise Http404('eh fiera para')

def encuesta(request):
    try:
        docente = Docente.objects.get(pk=request.POST['docente'])
    except (ValueError, KeyError, Turno.DoesNotExist):
        return render(request, 'encuestas/encuesta.html',
                      {'turnos': Turno.objects.all(),
                        'docentes': Docente.objects.all(),
                       'error_message': 'Esto esta mal, muy mal',
                        })
    else:
        opciones = []
        for opcion in range(1, 6):
            turno = Turno.objects.get(pk=request.POST['opcion{}'.format(opcion)])
            peso = int(request.POST['peso{}'.format(opcion)])
            opciones.append((turno, peso))

        return HttpResponseRedirect(reverse('final_de_encuesta'))

def final(request):
    return render(request, 'encuestas/final.html')
