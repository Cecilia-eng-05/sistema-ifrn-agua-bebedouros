from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.formats import number_format

from . import grafico, iqab
from .forms import ColetaForm, ResultadoRowForm, parse_turbidez
from .models import Bebedouro, Coleta, Resultado, TrocaFiltro
from .services import (
    JANELAS_LABELS,
    alertas_internos,
    alertas_publicos,
    aviso_filtro_incompativel,
    coletas_recentes,
    linhas_faltantes,
    media_coletas,
    publicar_coleta,
    recalcular_coleta,
    salvar_troca_filtro,
    serie_historica,
    situacao_atual_bebedouro,
    situacao_atual_bebedouros,
    situacao_filtro,
    ultima_coleta_publicada,
    ultimo_resultado,
)
from .validation import avisos_para_resultado


# Posição (x%, y%) de cada bebedouro na imagem do mapa do campus
# (bebedouros/static/bebedouros/img/mapa-campus.png), medida a partir dos
# pinos marcados manualmente numa cópia dessa mesma imagem. Um bebedouro
# sem posição aqui simplesmente não aparece no mapa.
POSICOES_MAPA = {
    1: (63.0, 25.9),
    2: (57.6, 28.1),
    3: (49.1, 16.3),
    4: (38.9, 28.9),
    5: (44.3, 49.6),
    6: (58.2, 51.9),
    7: (76.6, 58.5),
    8: (72.3, 71.1),
    9: (73.4, 68.1),
    10: (74.2, 43.7),
    11: (73.0, 20.7),
    12: (86.2, 28.9),
    13: (92.6, 31.9),
    14: (88.6, 36.7),
    15: (91.1, 42.2),
}


def mapa(request):
    situacoes = situacao_atual_bebedouros(apenas_publicadas=True)
    pontos = []
    for situacao in situacoes:
        posicao = POSICOES_MAPA.get(situacao["bebedouro"].numero)
        if posicao is None:
            continue
        pontos.append({**situacao, "x": posicao[0], "y": posicao[1]})
    coleta = ultima_coleta_publicada()
    return render(
        request,
        "bebedouros/mapa.html",
        {"pontos": pontos, "ultima_atualizacao": coleta.data if coleta else None},
    )


FAIXA_SLUGS = {
    "Excelente": "excelente",
    "Boa": "boa",
    "Regular": "regular",
    "Ruim": "ruim",
    "Crítica": "critica",
}


def entenda_iqab(request):
    # Pesos e faixas vêm de iqab.py para o texto público nunca divergir da
    # conta de verdade (DESENHO-PARTE-VISUAL.md §7).
    pesos = {
        "qfq": int(iqab.PESO_QFQ * 100),
        "qm": int(iqab.PESO_QM * 100),
        "co": int(iqab.PESO_CO * 100),
    }
    pesos_decimais = {
        "qfq": number_format(iqab.PESO_QFQ, 1),
        "qm": number_format(iqab.PESO_QM, 1),
        "co": number_format(iqab.PESO_CO, 1),
    }
    pesos_qfq = {
        "cloro": int(iqab.PESO_CLORO * 100),
        "turbidez": int(iqab.PESO_TURBIDEZ * 100),
        "ph": int(iqab.PESO_PH * 100),
        "nitrato": int(iqab.PESO_NITRATO * 100),
    }
    faixas = []
    for i, (minimo, nome) in enumerate(iqab.FAIXAS):
        maximo = 100 if i == 0 else int(iqab.FAIXAS[i - 1][0]) - 1
        faixas.append(
            {
                "minimo": int(minimo),
                "maximo": maximo,
                "nome": nome,
                "slug": FAIXA_SLUGS[nome],
            }
        )
    return render(
        request,
        "bebedouros/entenda_iqab.html",
        {
            "pesos": pesos,
            "pesos_decimais": pesos_decimais,
            "pesos_qfq": pesos_qfq,
            "faixas": faixas,
        },
    )


def alertas_publico(request):
    situacoes = situacao_atual_bebedouros(apenas_publicadas=True)
    coleta = ultima_coleta_publicada()
    return render(
        request,
        "bebedouros/alertas_publico.html",
        {
            "alertas": alertas_publicos(situacoes),
            "ultima_atualizacao": coleta.data if coleta else None,
        },
    )


@login_required
def coleta_list(request):
    return render(request, "bebedouros/coleta_list.html", {"coletas": Coleta.objects.all()})


@login_required
def inicio(request):
    situacoes = situacao_atual_bebedouros()
    alertas = alertas_internos(situacoes)
    return render(
        request,
        "bebedouros/inicio.html",
        {"situacoes": situacoes, "alertas": alertas},
    )


def bebedouro_detalhe(request, pk):
    bebedouro = get_object_or_404(Bebedouro, pk=pk)
    apenas_publicadas = not request.user.is_authenticated
    situacao = situacao_atual_bebedouro(bebedouro, apenas_publicadas=apenas_publicadas)
    pesos_iqab = {
        "qfq": int(iqab.PESO_QFQ * 100),
        "qm": int(iqab.PESO_QM * 100),
        "co": int(iqab.PESO_CO * 100),
    }
    janela = request.GET.get("janela", "12m")
    if janela not in ("6m", "12m", "tudo"):
        janela = "12m"

    pontos = serie_historica(bebedouro, janela, apenas_publicadas=apenas_publicadas)
    grafico_dados = grafico.montar_grafico(pontos, dominio_y=(0, 100))
    recentes = coletas_recentes(bebedouro, apenas_publicadas=apenas_publicadas)
    media = media_coletas(recentes)
    filtro = situacao_filtro(bebedouro, apenas_publicadas=apenas_publicadas)
    ultimo = ultimo_resultado(bebedouro, apenas_publicadas=apenas_publicadas)

    return render(
        request,
        "bebedouros/bebedouro_detalhe.html",
        {
            "bebedouro": bebedouro,
            "situacao": situacao,
            "pesos_iqab": pesos_iqab,
            "grafico": grafico_dados,
            "janela": janela,
            "janelas_labels": JANELAS_LABELS,
            "recentes": recentes,
            "media": media,
            "filtro": filtro,
            "ultimo": ultimo,
        },
    )


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
        turbidez = f"<{number_format(resultado.turbidez_valor)}"
    elif resultado.turbidez_abaixo_limite:
        turbidez = "<"
    elif resultado.turbidez_valor is not None:
        turbidez = number_format(resultado.turbidez_valor)
    else:
        turbidez = None
    troca = TrocaFiltro.objects.filter(
        coleta_id=resultado.coleta_id, bebedouro_id=resultado.bebedouro_id
    ).first()
    return {
        "cloro": resultado.cloro,
        "condutividade": resultado.condutividade,
        "nitrato": resultado.nitrato,
        "turbidez": turbidez,
        "ph": resultado.ph,
        "coliformes_totais": resultado.coliformes_totais,
        "ecoli": resultado.ecoli,
        "filtro": resultado.filtro,
        "troca_filtro": troca.data_troca if troca else None,
        "fora_de_operacao": resultado.fora_de_operacao,
        "observacao": resultado.observacao,
    }


def _linhas(coleta, dados_post=None):
    resultados = {r.bebedouro_id: r for r in coleta.resultados.select_related("bebedouro")}
    linhas = []
    for bebedouro in Bebedouro.objects.all():
        resultado = resultados.get(bebedouro.id)
        prefix = f"b{bebedouro.id}"
        if not bebedouro.ativo_em(coleta.data):
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


def _salvar_grade(coleta, dados_post):
    """Salva os valores enviados pela grade e recalcula o IQA-B.
    Retorna a lista de avisos (valores estranhos, turbidez não reconhecida)."""
    linhas = _linhas(coleta, dados_post)
    avisos = []
    for linha in linhas:
        if linha["bloqueada"]:
            continue
        bebedouro = linha["bebedouro"]
        form = linha["form"]
        form.is_valid()
        cd = form.cleaned_data
        try:
            turbidez_valor, turbidez_abaixo = parse_turbidez(cd.get("turbidez", ""))
        except ValueError as exc:
            turbidez_valor, turbidez_abaixo = None, False
            avisos.append(f"{bebedouro.codigo}: {exc}")
        numericos = {
            "cloro": cd.get("cloro"),
            "condutividade": cd.get("condutividade"),
            "nitrato": cd.get("nitrato"),
            "turbidez_valor": turbidez_valor,
            "ph": cd.get("ph"),
        }
        for msg in avisos_para_resultado(numericos):
            avisos.append(f"{bebedouro.codigo}: {msg}")
        Resultado.objects.update_or_create(
            coleta=coleta,
            bebedouro=bebedouro,
            defaults={
                **numericos,
                "turbidez_abaixo_limite": turbidez_abaixo,
                "coliformes_totais": cd.get("coliformes_totais") or "",
                "ecoli": cd.get("ecoli") or "",
                "filtro": cd.get("filtro") or "",
                "fora_de_operacao": cd.get("fora_de_operacao") or False,
                "observacao": cd.get("observacao") or "",
            },
        )
        salvar_troca_filtro(coleta, bebedouro, cd.get("troca_filtro"))
        aviso_filtro = aviso_filtro_incompativel(bebedouro, coleta, cd.get("filtro") or "")
        if aviso_filtro:
            avisos.append(aviso_filtro)
    recalcular_coleta(coleta)
    return avisos


@login_required
def lancamento(request, pk):
    coleta = get_object_or_404(Coleta, pk=pk)
    if request.method == "POST":
        avisos = _salvar_grade(coleta, request.POST)
        for aviso in avisos:
            messages.warning(request, aviso)
        if coleta.status == Coleta.RASCUNHO:
            messages.success(request, "Resultados salvos como rascunho.")
        else:
            messages.success(request, "Resultados atualizados.")
        return redirect("lancamento", pk=coleta.pk)
    return render(
        request,
        "bebedouros/lancamento.html",
        {"coleta": coleta, "linhas": _linhas(coleta)},
    )


@login_required
def publicar(request, pk):
    coleta = get_object_or_404(Coleta, pk=pk)
    if request.method != "POST":
        return redirect("lancamento", pk=pk)
    confirmando = request.POST.get("confirmar") == "1"
    if not confirmando:
        # O botão "Publicar" vive dentro do formulário da grade: salva o que
        # estiver na tela antes de checar e publicar, para nunca descartar em
        # silêncio uma edição feita sem passar por "Salvar rascunho".
        avisos = _salvar_grade(coleta, request.POST)
        for aviso in avisos:
            messages.warning(request, aviso)
    faltantes = linhas_faltantes(coleta)
    if faltantes and not confirmando:
        messages.warning(
            request, "Faltam resultados de: " + ", ".join(faltantes) + "."
        )
        return render(
            request,
            "bebedouros/publicar_confirma.html",
            {"coleta": coleta, "faltantes": faltantes},
        )
    publicar_coleta(coleta)
    messages.success(request, f"{coleta} publicada.")
    return redirect("inicio")


@login_required
def apagar(request, pk):
    coleta = get_object_or_404(Coleta, pk=pk)
    if request.method == "POST":
        coleta.delete()
        messages.success(request, "Coleta apagada.")
        return redirect("coleta_list")
    return render(request, "bebedouros/apagar_confirma.html", {"coleta": coleta})
