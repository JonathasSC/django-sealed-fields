import os

from django.core.files.base import ContentFile
from django.db import models
from django.db.models.fields.files import FieldFile, ImageFieldFile

from .file_mixin import EncryptedFileMixin

__all__ = ["EncryptedFileField", "EncryptedImageField"]


class EncryptedFieldFileMixin:
    """
    Arquivo cujo conteúdo é criptografado ao ser gravado no storage e descriptografado
    somente quando é lido. Carregar a instância do banco não acessa o storage.
    """

    def _get_file(self):
        self._require_file()
        if getattr(self, "_file", None) is None:
            with self.storage.open(self.name, "rb") as encrypted_file:
                content = self.field.cryptographer.decrypted(encrypted_file.read())
            self._file = ContentFile(content, name=self.name)
        return self._file

    file = property(_get_file, FieldFile._set_file, FieldFile._del_file)

    @property
    def size(self):
        # O storage guarda o conteúdo criptografado, que é maior; o tamanho real exige descriptografar
        self._require_file()
        return self.file.size

    def open(self, mode="rb"):
        self._require_file()
        self.file.open(mode)
        return self

    def save(self, name, content, save=True):
        content.seek(0)
        encrypted = ContentFile(self.field.cryptographer.encrypted(content.read()))

        name = self.field.generate_filename(self.instance, os.path.basename(name))
        self.name = self.storage.save(name, encrypted, max_length=self.field.max_length)

        # A instância recebe o conteúdo original (o ImageField calcula as dimensões a partir dele)
        if hasattr(self, "_set_instance_attribute"):
            self._set_instance_attribute(self.name, content)
        else:  # Django < 5.1
            setattr(self.instance, self.field.attname, self.name)
        self._committed = True

        if save:
            self.instance.save()

    save.alters_data = True


class EncryptedFieldFile(EncryptedFieldFileMixin, FieldFile):
    pass


class EncryptedImageFieldFile(EncryptedFieldFileMixin, ImageFieldFile):
    pass


class EncryptedFileFieldMixin:
    """
    Comportamento compartilhado pelos campos de arquivo criptografados.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cryptographer = EncryptedFileMixin()

    def pre_save(self, model_instance, add):
        file = getattr(model_instance, self.attname)
        if file and not file._committed and file.size == 0:
            # Arquivos vazios não são gravados, como na versão original
            setattr(model_instance, self.attname, None)
        return super().pre_save(model_instance, add)


class EncryptedFileField(EncryptedFileFieldMixin, models.FileField):
    """
    Um campo de arquivo criptografado.
    """

    attr_class = EncryptedFieldFile


class EncryptedImageField(EncryptedFileFieldMixin, models.ImageField):
    """
    Um campo de imagem criptografado.
    """

    attr_class = EncryptedImageFieldFile
