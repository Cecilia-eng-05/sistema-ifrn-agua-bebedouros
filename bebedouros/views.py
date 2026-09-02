from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render


@login_required
def coleta_list(request):
    return render(request, "bebedouros/coleta_list.html", {"coletas": []})


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
