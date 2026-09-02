from django import forms


class ColetaForm(forms.Form):
    data = forms.DateField(
        label="Data da coleta",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
