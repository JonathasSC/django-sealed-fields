from functools import lru_cache

from cryptography.fernet import Fernet, MultiFernet
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


def get_keys():
    """
    Chaves configuradas em ENCRYPTION_KEY, da mais nova para a mais antiga.

    ENCRYPTION_KEY aceita uma chave ou uma lista de chaves. A primeira é usada para
    criptografar; todas são aceitas para descriptografar, o que permite trocar a chave
    sem perder acesso aos dados antigos (veja o comando rotate_encryption_key).
    """
    keys = getattr(settings, "ENCRYPTION_KEY", None)
    if not keys:
        raise ImproperlyConfigured("ENCRYPTION_KEY must be set in your settings.")
    if isinstance(keys, (str, bytes)):
        keys = [keys]
    return tuple(key.encode() if isinstance(key, str) else key for key in keys)


@lru_cache(maxsize=8)
def _build_cipher(keys):
    try:
        return MultiFernet([Fernet(key) for key in keys])
    except (ValueError, TypeError) as e:
        raise ImproperlyConfigured(
            "ENCRYPTION_KEY contém uma chave Fernet inválida. Gere uma com "
            "Fernet.generate_key()."
        ) from e


def get_cipher():
    """
    MultiFernet com as chaves atuais do settings.
    """
    return _build_cipher(get_keys())


def get_primary_cipher():
    """
    Fernet apenas com a chave principal (a primeira de ENCRYPTION_KEY).
    """
    return _build_cipher(get_keys()[:1])
