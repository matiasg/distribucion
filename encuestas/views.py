from django.http import Http404, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse

from materias.models import Turno, Docente

def index(request):
    raise Http404('eh fiera para')

def encuesta(request):
    # import pdb; pdb.set_trace() # sac
    try:
        turno_elegido = Turno.objects.get(pk=request.POST['turno'])
    except (ValueError, KeyError, Turno.DoesNotExist):
        return render(request, 'encuestas/encuesta.html',
                      {'turnos': Turno.objects.all(),
                        'docentes': Docente.objects.all(),
                       'error_message': 'Esto esta mal, muy mal',
                        })
    else:
        print(request.POST['turno'])
        return HttpResponseRedirect(reverse('final_de_encuesta'))

def final(request):
    return render(request, 'encuestas/final.html')
