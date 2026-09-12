import tempfile
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image

from bebedouros.models import Bebedouro


def _imagem_grande(largura=2400, altura=1800):
    buffer = BytesIO()
    Image.new("RGB", (largura, altura), color="blue").save(buffer, format="JPEG")
    buffer.seek(0)
    return SimpleUploadedFile("foto.jpg", buffer.read(), content_type="image/jpeg")


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class FotoBebedouroTests(TestCase):
    def test_foto_grande_e_redimensionada_ao_salvar(self):
        b = Bebedouro.objects.create(numero=1, foto=_imagem_grande())
        with Image.open(b.foto) as imagem:
            self.assertLessEqual(max(imagem.size), 1600)
