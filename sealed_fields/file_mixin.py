from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings


class EncryptedFileMixin:

    def __init__(self):
        if not hasattr(settings, 'ENCRYPTION_KEY'):
            raise ValueError("ENCRYPTION_KEY must be set in your environment.")
        self.cipher = Fernet(settings.ENCRYPTION_KEY)

    def encrypted(self, content):
        """
        Criptografa o conteúdo.
        """

        if isinstance(content, str):
            content = content.encode()  # Garante que o conteúdo seja convertido para bytes

        elif not isinstance(content, bytes):
            raise ValueError("O conteúdo precisa ser uma string ou bytes para criptografia.")

        return self.cipher.encrypt(content)

    def decrypted(self, content):
        """
        Descriptografa o conteúdo.
        """

        try:
            return self.cipher.decrypt(content)
        except InvalidToken as e:
            raise ValueError("Erro ao descriptografar: chave incorreta ou conteúdo corrompido.") from e
