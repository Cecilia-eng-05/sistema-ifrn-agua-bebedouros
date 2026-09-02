from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ColetaForm
from .models import Coleta


@login_required
def coleta_list(request):
    return render(request, "bebedouros/coleta_list.html", {"coletas": Coleta.objects.all()})


@login_required
def coleta_nova(request):
    if request.method == "POST":
        form = ColetaForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data["data"]
            existente = Coleta.objects.filter(data=data).first()
            if existente:
                messages.error(
                    request,
                    f"Já existe uma coleta em {data:%d/%m/%Y}. Abra-a para editar.",
                )
                return render(
                    request,
                    "bebedouros/coleta_nova.html",
                    {"form": form, "existente": existente},
                )
            coleta = Coleta.objects.create(data=data)
            return redirect("lancamento", pk=coleta.pk)
    else:
        form = ColetaForm()
    return render(request, "bebedouros/coleta_nova.html", {"form": form})


@login_required
def lancamento(request, pk):
    return HttpResponse("stub")


@login_required
def publicar(request, pk):
    return HttpResponse("stub")


@login_required
def apagar(request, pk):
    return HttpResponse("stub")
