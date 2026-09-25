from cryptography.fernet import InvalidToken

from .crypto import get_cipher


class EncryptedFileMixin:
    @property
    def cipher(self):
        return get_cipher()

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
