import datetime

from django.utils import timezone

from . import iqab
from .models import Bebedouro, Coleta, Resultado


def linhas_faltantes(coleta):
    """Códigos dos bebedouros ativos sem resultado nesta coleta, ou com resultado
    vazio e sem o marcador 'fora de operação nesta data'. Ordenado por número."""
    resultados = {r.bebedouro_id: r for r in coleta.resultados.all()}
    faltantes = []
    for bebedouro in Bebedouro.objects.all():
        if not bebedouro.ativo_em(coleta.data):
            continue
        resultado = resultados.get(bebedouro.id)
        if resultado is None:
            faltantes.append(bebedouro.codigo)
        elif resultado.esta_vazio() and not resultado.fora_de_operacao:
            faltantes.append(bebedouro.codigo)
    return faltantes


def recalcular_coleta(coleta):
    """Recalcula e guarda o IQA-B de cada bebedouro desta coleta.
    Chamado sempre que a coleta é salva."""
    campos = [
        "iqab", "iqab_qfq", "iqab_qm", "iqab_co",
        "iqab_classificacao", "iqab_status", "metodologia_versao",
    ]
    for resultado in coleta.resultados.select_related("bebedouro"):
        d = iqab.calcular(resultado)
        resultado.iqab = d["iqab"]
        resultado.iqab_qfq = d["qfq"]
        resultado.iqab_qm = d["qm"]
        resultado.iqab_co = d["co"]
        resultado.iqab_classificacao = d["classificacao"]
        resultado.iqab_status = d["status"]
        resultado.metodologia_versao = d["versao"]
        resultado.save(update_fields=campos)


def publicar_coleta(coleta):
    coleta.status = Coleta.PUBLICADO
    coleta.publicada_em = timezone.now()
    coleta.save(update_fields=["status", "publicada_em", "atualizada_em"])


def _ultimo_resultado_valido(bebedouro, apenas_publicadas=False):
    """O Resultado mais recente deste bebedouro que tem algum dado de
    verdade — pula linhas vazias e linhas marcadas 'fora de operação'.
    Com apenas_publicadas=True, considera só coletas já publicadas (usado
    pela página pública do bebedouro — DEFINICAO-DO-PROJETO.md §7)."""
    resultados = (
        Resultado.objects.filter(bebedouro=bebedouro)
        .select_related("coleta")
        .order_by("-coleta__data")
    )
    if apenas_publicadas:
        resultados = resultados.filter(coleta__status=Coleta.PUBLICADO)
    for resultado in resultados:
        if not resultado.fora_de_operacao and not resultado.esta_vazio():
            return resultado
    return None


def ultimo_resultado(bebedouro, apenas_publicadas=False):
    """O Resultado da coleta mais recente deste bebedouro, sem pular
    linha vazia ou fora de operação (ao contrário de
    _ultimo_resultado_valido). Usado pela página do bebedouro para saber
    se o motivo de não haver um IQA-B atual é o bebedouro estar
    atualmente fora de operação, e mostrar isso em destaque."""
    resultados = (
        Resultado.objects.filter(bebedouro=bebedouro)
        .select_related("coleta")
        .order_by("-coleta__data")
    )
    if apenas_publicadas:
        resultados = resultados.filter(coleta__status=Coleta.PUBLICADO)
    return resultados.first()


def situacao_atual_bebedouros(apenas_publicadas=False):
    """Situação mais recente de cada bebedouro, para a tela Início e para
    o mapa público.

    Retorna uma lista, na mesma ordem de Bebedouro.objects.all() (por
    número), de dicts: {"bebedouro": Bebedouro, "resultado": Resultado ou
    None, "data": date ou None}. 'resultado' é o resultado não vazio mais
    recente daquele bebedouro; None se o bebedouro nunca teve um
    lançamento com dado. apenas_publicadas=True restringe às coletas já
    publicadas (usado pelo mapa, que é público)."""
    situacoes = []
    for bebedouro in Bebedouro.objects.all():
        resultado = _ultimo_resultado_valido(bebedouro, apenas_publicadas=apenas_publicadas)
        situacoes.append(
            {
                "bebedouro": bebedouro,
                "resultado": resultado,
                "data": resultado.coleta.data if resultado else None,
            }
        )
    return situacoes


def situacao_atual_bebedouro(bebedouro, apenas_publicadas=False):
    """Situação mais recente de UM bebedouro — mesmo formato de item de
    situacao_atual_bebedouros(), usado pela página do bebedouro (pública e
    interna). apenas_publicadas=True restringe às coletas já publicadas."""
    resultado = _ultimo_resultado_valido(bebedouro, apenas_publicadas=apenas_publicadas)
    return {
        "bebedouro": bebedouro,
        "resultado": resultado,
        "data": resultado.coleta.data if resultado else None,
    }


def alertas_internos(situacoes):
    """A partir da lista devolvida por situacao_atual_bebedouros(), monta
    os três alertas internos da tela Início: bebedouros ativos com IQA-B
    abaixo de 40, com filtro vencido, e os que faltam na coleta mais
    recente."""
    ativos = [s for s in situacoes if s["bebedouro"].ativo]
    iqab_ruim = [
        s
        for s in ativos
        if s["resultado"]
        and s["resultado"].iqab_status == iqab.CALCULADO
        and s["resultado"].iqab_classificacao in ("Ruim", "Crítica")
    ]
    filtro_vencido = [
        s
        for s in ativos
        if s["resultado"] and s["resultado"].filtro == Resultado.FILTRO_VENCIDO
    ]
    ultima_coleta = Coleta.objects.first()
    quinzena_sem_dados = linhas_faltantes(ultima_coleta) if ultima_coleta else []
    return {
        "iqab_ruim": iqab_ruim,
        "filtro_vencido": filtro_vencido,
        "quinzena_sem_dados": quinzena_sem_dados,
    }


JANELA_DIAS = {"6m": 182, "12m": 365}
JANELAS_LABELS = {"6m": "6 meses", "12m": "12 meses", "tudo": "Tudo"}


def serie_historica(bebedouro, janela, apenas_publicadas=False):
    """Pontos do IQA-B deste bebedouro ao longo do tempo, para o gráfico
    de evolução. 'janela' é uma chave de JANELA_DIAS ou 'tudo'. Retorna
    uma lista, em ordem cronológica, de {"data": date, "valor": Decimal
    ou None} — valor None marca uma coleta sem IQA-B calculado (o
    gráfico não deve emendar uma linha por cima desse ponto)."""
    resultados = (
        Resultado.objects.filter(bebedouro=bebedouro, fora_de_operacao=False)
        .select_related("coleta")
        .order_by("coleta__data")
    )
    if apenas_publicadas:
        resultados = resultados.filter(coleta__status=Coleta.PUBLICADO)
    if janela in JANELA_DIAS:
        limite = datetime.date.today() - datetime.timedelta(days=JANELA_DIAS[janela])
        resultados = resultados.filter(coleta__data__gte=limite)

    pontos = []
    for resultado in resultados:
        if resultado.esta_vazio():
            continue
        valor = resultado.iqab if resultado.iqab_status == iqab.CALCULADO else None
        pontos.append({"data": resultado.coleta.data, "valor": valor})
    return pontos


def historico_bebedouro(bebedouro, apenas_publicadas=False):
    """Coletas anteriores à situação atual deste bebedouro, dos últimos
    12 meses, para a lista 'Quinzenas anteriores' da página do bebedouro
    (a situação atual já aparece no topo da página, então não entra
    aqui). Retorna uma lista de Resultado, mais recente primeiro."""
    atual = _ultimo_resultado_valido(bebedouro, apenas_publicadas=apenas_publicadas)
    resultados = (
        Resultado.objects.filter(bebedouro=bebedouro)
        .select_related("coleta")
        .order_by("-coleta__data")
    )
    if apenas_publicadas:
        resultados = resultados.filter(coleta__status=Coleta.PUBLICADO)
    limite = datetime.date.today() - datetime.timedelta(days=JANELA_DIAS["12m"])
    resultados = resultados.filter(coleta__data__gte=limite)

    historico = []
    for resultado in resultados:
        if atual and resultado.pk == atual.pk:
            continue
        if resultado.esta_vazio() and not resultado.fora_de_operacao:
            continue
        historico.append(resultado)
    return historico
