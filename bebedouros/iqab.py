"""Cálculo do índice IQA-B.

Metodologia definida com a orientadora em 04/09/2026 (versão "1.0"):

    IQA-B = 0,3·QFQ + 0,5·QM + 0,2·CO

- QFQ (Físico-Química): média ponderada de Cloro (0,35), Turbidez (0,25),
  pH (0,20) e Nitrato (0,20), cada um pontuado 0/50/100 conforme os limites
  da Portaria MS nº 888/2021.
- QM (Microbiológica): E. coli PRESENTE zera o QM inteiro (contaminação
  fecal não se dilui em média). Caso contrário, média ponderada 0,70·E.coli
  + 0,30·Coliformes Totais (Presença=0, Ausência=100).
- CO (Operacional): só a situação do filtro — dentro da validade=100,
  vencido=0.
- Condutividade é monitorada mas não entra nesta fórmula.

Se a fórmula mudar de novo, muda só `VERSAO_METODOLOGIA` e as funções deste
módulo — o resto do sistema (armazenamento, recálculo ao salvar, exibição
na grade) já está pronto.
"""

from decimal import ROUND_HALF_UP, Decimal

VERSAO_METODOLOGIA = "1.0"

# Estados possíveis de um IQA-B calculado.
SEM_DADOS = "sem_dados"      # linha vazia ou fora de operação — nada a calcular
PENDENTE = "pendente"        # (histórico) linha calculada antes da fórmula existir
INCOMPLETO = "incompleto"    # há dados, mas falta algum parâmetro obrigatório
CALCULADO = "calculado"      # índice calculado

# Faixas de classificação do IQA-B final (definição do projeto, seção 8.1).
FAIXAS = [
    (Decimal("80"), "Excelente"),
    (Decimal("60"), "Boa"),
    (Decimal("40"), "Regular"),
    (Decimal("20"), "Ruim"),
    (Decimal("0"), "Crítica"),
]

# Limites de cada parâmetro do QFQ (Portaria MS nº 888/2021).
CLORO_MIN = Decimal("0.20")
CLORO_MAX = Decimal("5.0")
TURBIDEZ_BOA = Decimal("1")
TURBIDEZ_LIMITE = Decimal("5")
PH_MIN = Decimal("6")
PH_MAX = Decimal("9")
NITRATO_LIMITE = Decimal("10")

# Pesos do IQA-B final.
PESO_QFQ = Decimal("0.3")
PESO_QM = Decimal("0.5")
PESO_CO = Decimal("0.2")

# Pesos dentro do QFQ.
PESO_CLORO = Decimal("0.35")
PESO_TURBIDEZ = Decimal("0.25")
PESO_PH = Decimal("0.20")
PESO_NITRATO = Decimal("0.20")

# Pesos dentro do QM.
PESO_ECOLI = Decimal("0.70")
PESO_COLIFORMES = Decimal("0.30")

UMA_CASA = Decimal("0.1")


def _arredondar(valor):
    return valor.quantize(UMA_CASA, rounding=ROUND_HALF_UP)


def classificar(nota):
    """Nome da faixa para uma nota de 0 a 100. '' se a nota for None."""
    if nota is None:
        return ""
    for minimo, nome in FAIXAS:
        if nota >= minimo:
            return nome
    return "Crítica"


def _nota_cloro(valor):
    return Decimal(100) if CLORO_MIN <= valor <= CLORO_MAX else Decimal(0)


def _nota_turbidez(valor, abaixo_limite):
    if abaixo_limite:
        return Decimal(100)
    if valor <= TURBIDEZ_BOA:
        return Decimal(100)
    if valor <= TURBIDEZ_LIMITE:
        return Decimal(50)
    return Decimal(0)


def _nota_ph(valor):
    return Decimal(100) if PH_MIN <= valor <= PH_MAX else Decimal(0)


def _nota_nitrato(valor):
    return Decimal(100) if valor <= NITRATO_LIMITE else Decimal(0)


def _qfq(r):
    return (
        PESO_CLORO * _nota_cloro(r.cloro)
        + PESO_TURBIDEZ * _nota_turbidez(r.turbidez_valor, r.turbidez_abaixo_limite)
        + PESO_PH * _nota_ph(r.ph)
        + PESO_NITRATO * _nota_nitrato(r.nitrato)
    )


def _qm(r):
    if r.ecoli == r.PRESENTE:
        return Decimal(0)
    nota_coliformes = Decimal(100) if r.coliformes_totais == r.AUSENTE else Decimal(0)
    return PESO_ECOLI * Decimal(100) + PESO_COLIFORMES * nota_coliformes


def _co(r):
    return Decimal(100) if r.filtro == r.FILTRO_DENTRO else Decimal(0)


def _completo(r):
    """Todos os parâmetros obrigatórios da fórmula presentes nesta linha?
    (Condutividade não entra na fórmula, então não é obrigatória aqui.)"""
    if r.cloro is None or r.ph is None or r.nitrato is None:
        return False
    if r.turbidez_valor is None and not r.turbidez_abaixo_limite:
        return False
    if r.coliformes_totais not in (r.AUSENTE, r.PRESENTE):
        return False
    if r.ecoli not in (r.AUSENTE, r.PRESENTE):
        return False
    if r.filtro not in (r.FILTRO_DENTRO, r.FILTRO_VENCIDO):
        return False
    return True


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

    if not _completo(resultado):
        return _vazio(INCOMPLETO)

    qfq = _qfq(resultado)
    qm = _qm(resultado)
    co = _co(resultado)
    nota = _arredondar(PESO_QFQ * qfq + PESO_QM * qm + PESO_CO * co)

    return {
        "status": CALCULADO,
        "iqab": nota,
        "classificacao": classificar(nota),
        "qfq": _arredondar(qfq),
        "qm": _arredondar(qm),
        "co": _arredondar(co),
        "versao": VERSAO_METODOLOGIA,
    }
