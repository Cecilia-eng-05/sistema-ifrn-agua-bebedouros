from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ColetaForm, ResultadoRowForm, parse_turbidez
from .models import Bebedouro, Coleta, Resultado


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


def _initial_de(resultado):
    if resultado is None:
        return {}
    if resultado.turbidez_abaixo_limite and resultado.turbidez_valor is not None:
        turbidez = f"<{resultado.turbidez_valor}"
    elif resultado.turbidez_abaixo_limite:
        turbidez = "<"
    else:
        turbidez = resultado.turbidez_valor
    return {
        "cloro": resultado.cloro,
        "condutividade": resultado.condutividade,
        "nitrato": resultado.nitrato,
        "turbidez": turbidez,
        "ph": resultado.ph,
        "coliformes_totais": resultado.coliformes_totais,
        "ecoli": resultado.ecoli,
        "filtro": resultado.filtro,
        "fora_de_operacao": resultado.fora_de_operacao,
        "observacao": resultado.observacao,
    }


def _linhas(coleta, dados_post=None):
    resultados = {r.bebedouro_id: r for r in coleta.resultados.select_related("bebedouro")}
    linhas = []
    for bebedouro in Bebedouro.objects.all():
        resultado = resultados.get(bebedouro.id)
        prefix = f"b{bebedouro.id}"
        if not bebedouro.ativo:
            linhas.append(
                {"bebedouro": bebedouro, "bloqueada": True, "resultado": resultado, "form": None}
            )
            continue
        if dados_post is not None:
            form = ResultadoRowForm(dados_post, prefix=prefix)
        else:
            form = ResultadoRowForm(prefix=prefix, initial=_initial_de(resultado))
        linhas.append(
            {"bebedouro": bebedouro, "bloqueada": False, "resultado": resultado, "form": form}
        )
    return linhas


@login_required
def lancamento(request, pk):
    coleta = get_object_or_404(Coleta, pk=pk)
    return render(
        request,
        "bebedouros/lancamento.html",
        {"coleta": coleta, "linhas": _linhas(coleta)},
    )


@login_required
def publicar(request, pk):
    return HttpResponse("stub")


@login_required
def apagar(request, pk):
    return HttpResponse("stub")
