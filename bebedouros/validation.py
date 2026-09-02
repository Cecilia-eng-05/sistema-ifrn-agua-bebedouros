from decimal import Decimal

_ZERO = Decimal("0")
_QUATORZE = Decimal("14")


def avisos_para_resultado(dados):
    """dados: dict com chaves cloro, condutividade, nitrato, turbidez_valor, ph
    (Decimal ou None). Retorna lista de mensagens de aviso; nunca bloqueia nem levanta."""
    avisos = []
    ph = dados.get("ph")
    if ph is not None and (ph < _ZERO or ph > _QUATORZE):
        avisos.append(f"pH {ph} está fora da faixa 0–14.")
    for chave, rotulo in [
        ("cloro", "Cloro"),
        ("condutividade", "Condutividade"),
        ("nitrato", "Nitrato"),
        ("turbidez_valor", "Turbidez"),
    ]:
        valor = dados.get(chave)
        if valor is not None and valor < _ZERO:
            avisos.append(f"{rotulo} {valor} é negativo.")
    return avisos
