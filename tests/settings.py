import tempfile

from cryptography.fernet import Fernet

SECRET_KEY = "tests"
ENCRYPTION_KEY = Fernet.generate_key()
SERVE_DECRYPTED_FILE_URL_BASE = "serve/files/"

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "serve_files",
    "tests",
]

MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
]

DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
ROOT_URLCONF = "tests.urls"
MEDIA_ROOT = tempfile.mkdtemp(prefix="sealed-fields-tests-")
DEFAULT_AUTO_FIELD = "django.db.models.AutoField"
USE_TZ = True
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
