from . import iqab
from .models import Bebedouro, Coleta


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
    coleta.save(update_fields=["status", "atualizada_em"])
