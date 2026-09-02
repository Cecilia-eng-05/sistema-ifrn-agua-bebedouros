from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render

from .models import Coleta


@login_required
def coleta_list(request):
    return render(request, "bebedouros/coleta_list.html", {"coletas": Coleta.objects.all()})


@login_required
def coleta_nova(request):
    return HttpResponse("stub")


@login_required
def lancamento(request, pk):
    return HttpResponse("stub")


@login_required
def publicar(request, pk):
    return HttpResponse("stub")


@login_required
def apagar(request, pk):
    return HttpResponse("stub")
