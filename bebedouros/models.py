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
