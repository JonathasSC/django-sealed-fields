import logging
import os
from io import BytesIO

from django.core.files.base import ContentFile
from django.db import models
from PIL import Image

from .encrypted_file_mixin import EncryptedFileMixin

__all__ = ["EncryptedFileField", "EncryptedImageField"]

logger = logging.getLogger(__name__)


class EncryptedFileFieldMixin:
    """
    Comportamento compartilhado pelos campos de arquivo criptografados.

    O conteúdo é criptografado no `pre_save` e descriptografado no `from_db_value`.
    O arquivo descriptografado carrega o caminho de origem no storage, o que permite
    salvar a instância novamente sem recriptografar nem duplicar o arquivo.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cryptographer = EncryptedFileMixin()

    def pre_save(self, model_instance, add):
        file = getattr(model_instance, self.attname)

        if not file:
            model_instance.__dict__[self.attname] = None
            return super().pre_save(model_instance, add)

        if file._committed:
            # Arquivo já persistido (por exemplo, na segunda chamada de pre_save do Django 6).
            return super().pre_save(model_instance, add)

        source_name = getattr(getattr(file, "_file", None), "_sealed_source_name", None)
        if source_name is not None:
            # Valor carregado do banco e não alterado: mantém o arquivo já criptografado.
            return source_name

        if file.size == 0:
            model_instance.__dict__[self.attname] = None
            return super().pre_save(model_instance, add)

        file.name = os.path.basename(file.name)
        model_instance.__dict__[self.attname] = self._encrypt_file(file)
        return super().pre_save(model_instance, add)

    def _encrypt_file(self, file):
        """
        Criptografa o conteúdo do arquivo antes de ser salvo.
        """
        file.seek(0)
        encrypted_content = self.cryptographer.encrypted(file.read())
        return ContentFile(encrypted_content, name=file.name)

    def from_db_value(self, value, expression, connection):
        """
        Descriptografa o arquivo ao ser carregado do banco de dados.
        Se o valor for vazio, retorna None. Se o arquivo não existir no storage,
        retorna o caminho sem descriptografar.
        """
        if not value:
            return None

        if not self.storage.exists(value):
            logger.warning("Arquivo criptografado não encontrado no storage: %s", value)
            return value

        with self.storage.open(value, "rb") as encrypted_file:
            decrypted_content = self.cryptographer.decrypted(encrypted_file.read())

        self._validate_decrypted_content(decrypted_content)
        decrypted_file = ContentFile(decrypted_content, name=value)
        decrypted_file._sealed_source_name = value
        return decrypted_file

    def _validate_decrypted_content(self, content):
        """
        Sobrescreva para validar o conteúdo descriptografado.
        """


class EncryptedFileField(EncryptedFileFieldMixin, models.FileField):
    """
    Um campo de arquivo criptografado.
    """


class EncryptedImageField(EncryptedFileFieldMixin, models.ImageField):
    """
    Um campo de imagem criptografado.
    """

    def _validate_decrypted_content(self, content):
        try:
            Image.open(BytesIO(content)).verify()
        except Exception as e:
            raise ValueError(f"A decriptação falhou, o conteúdo não é uma imagem válida: {e}")
