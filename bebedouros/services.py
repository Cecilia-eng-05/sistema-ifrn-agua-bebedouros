import datetime
from decimal import Decimal

from django.utils import timezone
from django.utils.formats import number_format

from . import iqab
from .models import Bebedouro, Coleta, Resultado, TrocaFiltro, formatar_turbidez


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


def coletas_recentes(bebedouro, apenas_publicadas=False, quantidade=5):
    """As `quantidade` coletas mais recentes deste bebedouro que têm
    resultado de verdade — a atual incluída — para o bloco 'Coletas
    recentes' da página do bebedouro. Mais recente primeiro. Pula linhas
    totalmente vazias E as marcadas 'fora de operação' (essa situação já
    aparece no topo da página quando é a atual; uma fora de operação no
    passado simplesmente não entra nesta lista nem na média — não há
    resultado para mostrar). apenas_publicadas=True restringe às coletas
    já publicadas."""
    resultados = (
        Resultado.objects.filter(bebedouro=bebedouro)
        .select_related("coleta")
        .order_by("-coleta__data")
    )
    if apenas_publicadas:
        resultados = resultados.filter(coleta__status=Coleta.PUBLICADO)

    recentes = []
    for resultado in resultados:
        if resultado.esta_vazio() or resultado.fora_de_operacao:
            continue
        recentes.append(resultado)
        if len(recentes) == quantidade:
            break
    return recentes


# Casas decimais de cada campo — mesma precisão do respectivo
# DecimalField em Resultado (models.py). Necessário porque uma média
# raramente fecha exato: sem arredondar pra essa precisão, "1+1+2"/3
# vira uma dízima gigante em vez de "1,333".
_CASAS_DECIMAIS = {
    "cloro": Decimal("0.001"),
    "condutividade": Decimal("0.001"),
    "nitrato": Decimal("0.001"),
    "ph": Decimal("0.01"),
}
_CASAS_TURBIDEZ = Decimal("0.001")


def media_coletas(resultados):
    """Média dos parâmetros de uma lista de Resultado (normalmente a
    saída de coletas_recentes()), para o bloco 'Média das coletas
    recentes' da página do bebedouro. Coletas marcadas fora de operação
    ficam de fora de toda a conta. Retorna um dict já pronto para
    exibir — cada valor é uma string ('—' quando não há dado nenhum)."""
    validos = [r for r in resultados if not r.fora_de_operacao]

    def texto_decimal(campo):
        valores = [getattr(r, campo) for r in validos if getattr(r, campo) is not None]
        if not valores:
            return "—"
        media = sum(valores) / len(valores)
        return number_format(media.quantize(_CASAS_DECIMAIS[campo]))

    turbidez_valores = []
    turbidez_abaixo = False
    for r in validos:
        if r.turbidez_valor is None:
            continue
        turbidez_valores.append(r.turbidez_valor)
        if r.turbidez_abaixo_limite:
            turbidez_abaixo = True
    turbidez_media = None
    if turbidez_valores:
        turbidez_media = (
            sum(turbidez_valores) / len(turbidez_valores)
        ).quantize(_CASAS_TURBIDEZ)
    turbidez_texto = formatar_turbidez(turbidez_media, turbidez_abaixo) or "—"

    def texto_micro(campo):
        respondidos = [
            getattr(r, campo)
            for r in validos
            if getattr(r, campo) in (Resultado.AUSENTE, Resultado.PRESENTE)
        ]
        total = len(respondidos)
        if total == 0:
            return "—", False
        presentes = sum(1 for v in respondidos if v == Resultado.PRESENTE)
        palavra = "coleta" if total == 1 else "coletas"
        if presentes > 0:
            return f"Presente em {presentes} de {total} {palavra}", True
        return f"Ausente em {total} de {total} {palavra}", False

    coliformes_texto, coliformes_alerta = texto_micro("coliformes_totais")
    ecoli_texto, ecoli_alerta = texto_micro("ecoli")

    notas = [
        r.iqab for r in validos if r.iqab_status == iqab.CALCULADO and r.iqab is not None
    ]
    media_iqab = iqab.media(notas)
    iqab_texto = (
        f"{number_format(media_iqab)} · {iqab.classificar(media_iqab)}"
        if media_iqab is not None
        else "—"
    )

    return {
        "quantidade": len(validos),
        "cloro": texto_decimal("cloro"),
        "condutividade": texto_decimal("condutividade"),
        "nitrato": texto_decimal("nitrato"),
        "ph": texto_decimal("ph"),
        "turbidez": turbidez_texto,
        "coliformes_totais": coliformes_texto,
        "coliformes_totais_alerta": coliformes_alerta,
        "ecoli": ecoli_texto,
        "ecoli_alerta": ecoli_alerta,
        "iqab_texto": iqab_texto,
    }


VALIDADE_FILTRO_DIAS = 182  # ~6 meses — mesma aproximação de JANELA_DIAS["6m"]


def ultima_troca_filtro(bebedouro, apenas_publicadas=False):
    """A troca de filtro mais recente registrada para este bebedouro, ou
    None se nunca houve uma (ou nenhuma visível). apenas_publicadas=True
    restringe às trocas lançadas em coletas já publicadas."""
    trocas = TrocaFiltro.objects.filter(bebedouro=bebedouro).select_related("coleta")
    if apenas_publicadas:
        trocas = trocas.filter(coleta__status=Coleta.PUBLICADO)
    return trocas.order_by("-data_troca").first()


def situacao_filtro(bebedouro, apenas_publicadas=False):
    """Situação da manutenção do filtro deste bebedouro, para o bloco
    'Manutenção do filtro' da página do bebedouro. Retorna
    {"status": "sem_registro"|"ok"|"vencido", "data_troca": date|None,
    "data_vencimento": date|None}."""
    troca = ultima_troca_filtro(bebedouro, apenas_publicadas=apenas_publicadas)
    if troca is None:
        return {"status": "sem_registro", "data_troca": None, "data_vencimento": None}
    vencimento = troca.data_troca + datetime.timedelta(days=VALIDADE_FILTRO_DIAS)
    status = "ok" if datetime.date.today() <= vencimento else "vencido"
    return {"status": status, "data_troca": troca.data_troca, "data_vencimento": vencimento}


def salvar_troca_filtro(coleta, bebedouro, data_troca):
    """Cria, atualiza ou remove o registro de troca de filtro lançado
    nesta coleta para este bebedouro. data_troca=None remove o registro,
    se houver — é o que a grade envia quando o bolsista apaga a data."""
    if data_troca is None:
        TrocaFiltro.objects.filter(coleta=coleta, bebedouro=bebedouro).delete()
        return
    TrocaFiltro.objects.update_or_create(
        coleta=coleta, bebedouro=bebedouro, defaults={"data_troca": data_troca}
    )


def _filtro_esperado(bebedouro, data_coleta):
    """O que o campo Filtro (dentro/vencido) desta coleta deveria dizer,
    segundo a troca de filtro mais recente registrada ATÉ essa data (uma
    troca lançada depois não conta — não dá pra julgar o passado com
    informação do futuro). None se não há nenhuma troca conhecida até
    essa data — nada a comparar."""
    troca = (
        TrocaFiltro.objects.filter(bebedouro=bebedouro, data_troca__lte=data_coleta)
        .order_by("-data_troca")
        .first()
    )
    if troca is None:
        return None
    vencimento = troca.data_troca + datetime.timedelta(days=VALIDADE_FILTRO_DIAS)
    return Resultado.FILTRO_DENTRO if data_coleta <= vencimento else Resultado.FILTRO_VENCIDO


def aviso_filtro_incompativel(bebedouro, coleta, filtro_escolhido):
    """Se houver troca de filtro registrada até a data desta coleta e o
    valor escolhido no campo Filtro não bater com o que a regra dos 6
    meses esperaria, retorna um aviso pronto para mostrar ao bolsista ao
    salvar a grade. None quando não há nada para comparar (nenhuma troca
    conhecida até essa data, ou o campo Filtro em branco) ou quando os
    dois batem certinho."""
    if not filtro_escolhido:
        return None
    esperado = _filtro_esperado(bebedouro, coleta.data)
    if esperado is None or esperado == filtro_escolhido:
        return None
    rotulos = dict(Resultado.FILTRO_CHOICES)
    return (
        f'{bebedouro.codigo}: pela última troca de filtro registrada, o esperado aqui '
        f'seria "{rotulos[esperado]}", mas foi marcado "{rotulos[filtro_escolhido]}".'
    )
