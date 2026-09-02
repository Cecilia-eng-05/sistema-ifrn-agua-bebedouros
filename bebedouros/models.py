from django.db import models


class Bebedouro(models.Model):
    numero = models.PositiveSmallIntegerField(unique=True)
    local = models.CharField(max_length=200, blank=True)
    # Data em que o bebedouro saiu de operação por tempo indeterminado.
    # Vazio = em operação. Coletas anteriores a essa data não são afetadas.
    desativado_em = models.DateField("Desativado em", null=True, blank=True)

    class Meta:
        ordering = ["numero"]

    @property
    def codigo(self):
        return f"B{self.numero}"

    @property
    def ativo(self):
        return self.desativado_em is None

    def ativo_em(self, data):
        """Estava em operação na data desta coleta?"""
        return self.desativado_em is None or data < self.desativado_em

    def __str__(self):
        return self.codigo


class Coleta(models.Model):
    RASCUNHO = "rascunho"
    PUBLICADO = "publicado"
    STATUS_CHOICES = [(RASCUNHO, "Rascunho"), (PUBLICADO, "Publicado")]

    data = models.DateField(unique=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=RASCUNHO)
    criada_em = models.DateTimeField(auto_now_add=True)
    atualizada_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-data"]

    def __str__(self):
        return f"Coleta de {self.data:%d/%m/%Y}"

    @property
    def publicada(self):
        return self.status == self.PUBLICADO


class Resultado(models.Model):
    AUSENTE = "AUSENTE"
    PRESENTE = "PRESENTE"
    MICRO_CHOICES = [("", "—"), (AUSENTE, "Ausente"), (PRESENTE, "Presente")]

    FILTRO_DENTRO = "dentro"
    FILTRO_VENCIDO = "vencido"
    FILTRO_CHOICES = [
        ("", "—"),
        (FILTRO_DENTRO, "Dentro da validade"),
        (FILTRO_VENCIDO, "Vencido"),
    ]

    coleta = models.ForeignKey(Coleta, on_delete=models.CASCADE, related_name="resultados")
    bebedouro = models.ForeignKey(Bebedouro, on_delete=models.PROTECT, related_name="resultados")

    fora_de_operacao = models.BooleanField(default=False)
    observacao = models.CharField(max_length=200, blank=True)

    cloro = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    condutividade = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    nitrato = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    turbidez_valor = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    turbidez_abaixo_limite = models.BooleanField(default=False)
    ph = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    coliformes_totais = models.CharField(max_length=10, choices=MICRO_CHOICES, blank=True, default="")
    ecoli = models.CharField(max_length=10, choices=MICRO_CHOICES, blank=True, default="")
    filtro = models.CharField(max_length=10, choices=FILTRO_CHOICES, blank=True, default="")

    # IQA-B calculado a partir dos campos acima. Preenchido pelo sistema ao
    # salvar a coleta; a fórmula em si (bebedouros/iqab.py) ainda é pendente.
    iqab = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    iqab_qfq = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    iqab_qm = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    iqab_co = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    iqab_classificacao = models.CharField(max_length=12, blank=True, default="")
    iqab_status = models.CharField(max_length=12, blank=True, default="")
    metodologia_versao = models.CharField(max_length=20, blank=True, default="")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["coleta", "bebedouro"],
                name="uniq_resultado_por_bebedouro_na_coleta",
            )
        ]

    def __str__(self):
        return f"{self.bebedouro.codigo} @ {self.coleta.data:%d/%m/%Y}"

    def iqab_texto(self):
        """Texto do IQA-B para mostrar na grade."""
        from . import iqab as _iqab

        if self.iqab_status == _iqab.CALCULADO and self.iqab is not None:
            return f"{self.iqab} · {self.iqab_classificacao}"
        if self.iqab_status == _iqab.PENDENTE:
            return "pendente"
        if self.iqab_status == _iqab.INCOMPLETO:
            return "incompleto"
        return "—"

    def iqab_faixa_slug(self):
        """Slug da faixa para colorir a célula ('' quando não há número)."""
        mapa = {
            "Excelente": "excelente",
            "Boa": "boa",
            "Regular": "regular",
            "Ruim": "ruim",
            "Crítica": "critica",
        }
        return mapa.get(self.iqab_classificacao, "")

    def esta_vazio(self):
        numericos = [self.cloro, self.condutividade, self.nitrato, self.turbidez_valor, self.ph]
        if any(v is not None for v in numericos):
            return False
        if self.turbidez_abaixo_limite:
            return False
        if self.coliformes_totais or self.ecoli or self.filtro:
            return False
        if self.observacao:
            return False
        return True
