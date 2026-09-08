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


def _ultimo_resultado_valido(bebedouro):
    """O Resultado mais recente deste bebedouro que tem algum dado de
    verdade — pula linhas vazias e linhas marcadas 'fora de operação'."""
    resultados = (
        Resultado.objects.filter(bebedouro=bebedouro)
        .select_related("coleta")
        .order_by("-coleta__data")
    )
    for resultado in resultados:
        if not resultado.fora_de_operacao and not resultado.esta_vazio():
            return resultado
    return None


def situacao_atual_bebedouros():
    """Situação mais recente de cada bebedouro, para a tela Início.

    Retorna uma lista, na mesma ordem de Bebedouro.objects.all() (por
    número), de dicts: {"bebedouro": Bebedouro, "resultado": Resultado ou
    None, "data": date ou None}. 'resultado' é o resultado não vazio mais
    recente daquele bebedouro; None se o bebedouro nunca teve um
    lançamento com dado."""
    situacoes = []
    for bebedouro in Bebedouro.objects.all():
        resultado = _ultimo_resultado_valido(bebedouro)
        situacoes.append(
            {
                "bebedouro": bebedouro,
                "resultado": resultado,
                "data": resultado.coleta.data if resultado else None,
            }
        )
    return situacoes


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
