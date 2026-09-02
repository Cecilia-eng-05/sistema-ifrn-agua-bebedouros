from django.db import models


class Bebedouro(models.Model):
    numero = models.PositiveSmallIntegerField(unique=True)
    local = models.CharField(max_length=200, blank=True)
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ["numero"]

    @property
    def codigo(self):
        return f"B{self.numero}"

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
