from cryptography.fernet import Fernet
from django.conf import settings


class EncryptedFieldMixin:
    """
    Mixin genérico para adicionar criptografia/descriptografia a campos do Django.

    O valor passa primeiro pelo get_prep_value do campo original (conversão e validação
    de tipo), é serializado em texto por `serialize_value`, criptografado e gravado em uma
    coluna de texto. Na leitura, o texto descriptografado é convertido de volta por
    `cast_value`, que por padrão usa o to_python do campo original.
    """
    def __init__(self, *args, **kwargs):
        if not hasattr(settings, 'ENCRYPTION_KEY'):
            raise ValueError("ENCRYPTION_KEY must be set in your environment.")
        self.cipher = Fernet(settings.ENCRYPTION_KEY)
        super().__init__(*args, **kwargs)

    def get_db_prep_value(self, value, connection, prepared=False):
        """
        Criptografa o valor antes de salvar no banco de dados.
        """
        if not prepared:
            value = self.get_prep_value(value)
        if value is None:
            return None
        return self.cipher.encrypt(self.serialize_value(value).encode()).decode()

    def get_db_prep_save(self, value, connection):
        # Alguns campos (como o DecimalField no Django 4.2) sobrescrevem este método sem
        # passar por get_db_prep_value, o que gravaria o valor sem criptografia.
        if hasattr(value, "as_sql"):
            return value
        return self.get_db_prep_value(value, connection, prepared=False)

    def from_db_value(self, value, expression, connection):
        """
        Descriptografa o valor ao recuperar do banco de dados.
        """
        if value is None:
            return value
        return self.cast_value(self.cipher.decrypt(value.encode()).decode())

    def serialize_value(self, value):
        """
        Converte o valor já preparado em texto antes da criptografia.
        """
        return str(value)

    def cast_value(self, value):
        """
        Converte o texto descriptografado de volta para o tipo do campo.
        """
        return self.to_python(value)

    def get_internal_type(self):
        return "TextField"
