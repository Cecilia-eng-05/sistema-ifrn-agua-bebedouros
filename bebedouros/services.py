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


def publicar_coleta(coleta):
    coleta.status = Coleta.PUBLICADO
    coleta.save(update_fields=["status", "atualizada_em"])
