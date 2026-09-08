"""Geometria do gráfico de evolução do bebedouro.

Funções puras (sem Django, sem banco): transformam uma série de pontos
{"data": date, "valor": Decimal ou None} nas coordenadas prontas para
desenhar um SVG. Segue o mesmo espírito de bebedouros/iqab.py — uma conta
isolada, fácil de testar sozinha, chamada pela view em views.py e
desenhada pelo template bebedouro_detalhe.html.
"""

LARGURA = 760
ALTURA = 220
MARGEM_ESQ = 34
MARGEM_DIR = 10
MARGEM_TOPO = 10
MARGEM_BASE = 24

# (nota mínima, nota máxima, slug) — mesmos slugs de faixa usados pelas
# classes .gota-*/.chip-* já existentes (ver base.html).
FAIXAS_IQAB = [
    (0, 20, "critica"),
    (20, 40, "ruim"),
    (40, 60, "regular"),
    (60, 80, "boa"),
    (80, 100, "excelente"),
]


def _escala(valor, minimo, maximo, destino_min, destino_max):
    if maximo == minimo:
        return (destino_min + destino_max) / 2
    fracao = (valor - minimo) / (maximo - minimo)
    return destino_min + fracao * (destino_max - destino_min)


def montar_grafico(pontos, dominio_y=None):
    """pontos: lista de {"data": date, "valor": Decimal ou None}, em
    ordem cronológica. dominio_y: (mínimo, máximo) fixo — passe (0, 100)
    para o IQA-B, para as faixas baterem com a escala; None calcula a
    escala a partir dos valores presentes (usado para um parâmetro).

    Retorna None se não houver nenhum ponto com valor. Senão, um dict
    com as coordenadas prontas para o template desenhar: largura, altura,
    area_esq/area_dir/area_topo/area_base, largura_area, segmentos (lista
    de listas de {"x", "y", "data", "valor"}, quebrada a cada valor
    ausente), faixas (None, ou as 5 faixas de classificação quando
    dominio_y é (0, 100)), data_min, data_max."""
    com_valor = [p for p in pontos if p["valor"] is not None]
    if not com_valor:
        return None

    area_esq, area_dir = MARGEM_ESQ, LARGURA - MARGEM_DIR
    area_topo, area_base = MARGEM_TOPO, ALTURA - MARGEM_BASE

    datas = [p["data"] for p in pontos]
    data_min, data_max = min(datas), max(datas)
    intervalo_dias = (data_max - data_min).days or 1

    if dominio_y is not None:
        y_min, y_max = dominio_y
    else:
        valores = [float(p["valor"]) for p in com_valor]
        y_min, y_max = min(valores), max(valores)
        if y_min == y_max:
            y_min, y_max = y_min - 1, y_max + 1
        else:
            folga = (y_max - y_min) * 0.1
            y_min -= folga
            y_max += folga
        y_min = min(y_min, 0)

    segmentos = []
    atual = []
    for p in pontos:
        if p["valor"] is None:
            if atual:
                segmentos.append(atual)
                atual = []
            continue
        x = _escala((p["data"] - data_min).days, 0, intervalo_dias, area_esq, area_dir)
        y = _escala(float(p["valor"]), y_min, y_max, area_base, area_topo)
        atual.append({"x": x, "y": y, "data": p["data"], "valor": p["valor"]})
    if atual:
        segmentos.append(atual)

    faixas = None
    if dominio_y == (0, 100):
        faixas = []
        for minimo, maximo, slug in FAIXAS_IQAB:
            y_topo = _escala(maximo, y_min, y_max, area_base, area_topo)
            y_base = _escala(minimo, y_min, y_max, area_base, area_topo)
            faixas.append({"y": y_topo, "altura": y_base - y_topo, "slug": slug})

    return {
        "largura": LARGURA,
        "altura": ALTURA,
        "area_esq": area_esq,
        "area_dir": area_dir,
        "area_topo": area_topo,
        "area_base": area_base,
        "largura_area": area_dir - area_esq,
        "segmentos": segmentos,
        "faixas": faixas,
        "data_min": data_min,
        "data_max": data_max,
    }
