"""Cálculo do índice IQA-B.

A fórmula final (pontuação por parâmetro e combinação de QFQ / QM / CO) ainda
é uma decisão metodológica pendente do TCC. Enquanto isso, `calcular` devolve
o estado 'pendente' para linhas com dados. Quando a metodologia for definida,
só esta função muda — o resto do sistema (armazenamento, recálculo ao salvar,
exibição na grade) já está pronto.
"""

from decimal import Decimal

# Identifica qual metodologia gerou cada IQA-B guardado. Troque quando a
# fórmula for definida (ex.: "1.0").
VERSAO_METODOLOGIA = "0-pendente"

# Estados possíveis de um IQA-B calculado.
SEM_DADOS = "sem_dados"      # linha vazia ou fora de operação — nada a calcular
PENDENTE = "pendente"        # há dados, mas a fórmula ainda não foi definida
INCOMPLETO = "incompleto"    # (futuro) dados insuficientes para a fórmula
CALCULADO = "calculado"      # (futuro) índice calculado

# Faixas de classificação do IQA-B final (definição do projeto, seção 8.1).
FAIXAS = [
    (Decimal("80"), "Excelente"),
    (Decimal("60"), "Boa"),
    (Decimal("40"), "Regular"),
    (Decimal("20"), "Ruim"),
    (Decimal("0"), "Crítica"),
]


def classificar(nota):
    """Nome da faixa para uma nota de 0 a 100. '' se a nota for None."""
    if nota is None:
        return ""
    for minimo, nome in FAIXAS:
        if nota >= minimo:
            return nome
    return "Crítica"


def _vazio(status):
    return {
        "status": status,
        "iqab": None,
        "classificacao": "",
        "qfq": None,
        "qm": None,
        "co": None,
        "versao": VERSAO_METODOLOGIA,
    }


def calcular(resultado):
    """Calcula o IQA-B de um Resultado.

    Retorna um dict: status, iqab, classificacao, qfq, qm, co, versao.
    """
    if resultado.fora_de_operacao or resultado.esta_vazio():
        return _vazio(SEM_DADOS)

    # Há dados na linha, mas a metodologia do TCC ainda não foi definida.
    return _vazio(PENDENTE)
