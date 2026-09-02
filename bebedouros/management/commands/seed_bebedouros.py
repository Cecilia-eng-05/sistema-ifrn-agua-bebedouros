from django.core.management.base import BaseCommand

from bebedouros.models import Bebedouro

LOCAIS = {
    1: "Mesas verdes",
    2: "Piscinas",
    3: "Marcenaria",
    4: "Quadra 3",
    5: "Quadra 1",
    6: "Biblioteca",
    7: "Campo",
    8: "Bloco C",
    9: "Bloco B",
    10: "Bloco D",
    11: "DIATINF",
    12: "DIACON",
    13: "DIAC",
    14: "DIAREN 1",
    15: "DIAREN 2",
}


class Command(BaseCommand):
    help = "Cria B1..B15 com os locais reais se ainda não existirem."

    def handle(self, *args, **options):
        criados = 0
        for numero, local in LOCAIS.items():
            _, novo = Bebedouro.objects.get_or_create(
                numero=numero, defaults={"local": local}
            )
            criados += int(novo)
        self.stdout.write(self.style.SUCCESS(f"{criados} bebedouro(s) criado(s)."))
