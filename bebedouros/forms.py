from decimal import Decimal, InvalidOperation

from django import forms

from .models import Resultado


class ColetaForm(forms.Form):
    data = forms.DateField(
        label="Data da coleta",
        widget=forms.DateInput(attrs={"type": "date"}),
    )


def parse_turbidez(texto):
    """Aceita '', '0,751', '0.751', '<0,751', '< 0.751'.
    Retorna (Decimal|None, abaixo_limite: bool). Levanta ValueError se não reconhecer."""
    if texto is None:
        return None, False
    t = texto.strip().replace(" ", "").replace(",", ".")
    if t == "":
        return None, False
    abaixo = False
    if t.startswith("<"):
        abaixo = True
        t = t[1:]
    try:
        return Decimal(t), abaixo
    except InvalidOperation:
        raise ValueError(f"Valor de turbidez não reconhecido: {texto!r}")


class ResultadoRowForm(forms.Form):
    cloro = forms.DecimalField(required=False, localize=True)
    condutividade = forms.DecimalField(required=False, localize=True)
    nitrato = forms.DecimalField(required=False, localize=True)
    turbidez = forms.CharField(required=False)
    ph = forms.DecimalField(required=False, localize=True)
    coliformes_totais = forms.ChoiceField(required=False, choices=Resultado.MICRO_CHOICES)
    ecoli = forms.ChoiceField(required=False, choices=Resultado.MICRO_CHOICES)
    filtro = forms.ChoiceField(required=False, choices=Resultado.FILTRO_CHOICES)
    fora_de_operacao = forms.BooleanField(required=False)
    observacao = forms.CharField(required=False, max_length=200)
