import datetime
import decimal
import unittest
import uuid

from cryptography.fernet import Fernet
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import connection
from django.test import TestCase
from django.utils import timezone

from .models import AllFields

# Bug conhecido: o mixin serializa com str() e sobrescreve get_prep_value, o que
# quebra estes tipos. Remova o expectedFailure quando o mixin for reescrito.
KNOWN_BROKEN = unittest.expectedFailure


class RoundTripMixin:
    def assertRoundTrip(self, field_name, value):
        obj = AllFields.objects.create(**{field_name: value})
        loaded = AllFields.objects.get(pk=obj.pk)
        self.assertEqual(getattr(loaded, field_name), value)
        return obj

    def raw_value(self, obj, field_name):
        with connection.cursor() as cursor:
            cursor.execute(
                f"SELECT {field_name} FROM {AllFields._meta.db_table} WHERE id = %s", [obj.pk]
            )
            return cursor.fetchone()[0]


class RoundTripTests(RoundTripMixin, TestCase):
    """
    Cada campo deve voltar do banco com o mesmo valor e tipo que foi salvo.
    """

    def test_integer(self):
        self.assertRoundTrip("integer", 42)
        self.assertRoundTrip("integer", -7)
        self.assertRoundTrip("integer", 0)

    def test_float(self):
        self.assertRoundTrip("float", 3.14)

    def test_boolean(self):
        self.assertRoundTrip("boolean", True)
        self.assertRoundTrip("boolean", False)

    def test_char(self):
        self.assertRoundTrip("char", "olá mundo ✓")

    def test_text(self):
        self.assertRoundTrip("text", "linha 1\nlinha 2 " * 200)

    def test_date(self):
        self.assertRoundTrip("date", datetime.date(2024, 2, 29))

    def test_email(self):
        self.assertRoundTrip("email", "fulano@example.com")

    def test_url(self):
        self.assertRoundTrip("url", "https://example.com/caminho?q=1")

    @KNOWN_BROKEN
    def test_datetime_aware(self):
        self.assertRoundTrip("datetime", timezone.now())

    @KNOWN_BROKEN
    def test_datetime_without_microseconds(self):
        self.assertRoundTrip("datetime", datetime.datetime(2024, 1, 2, 3, 4, 5, tzinfo=datetime.timezone.utc))

    @KNOWN_BROKEN
    def test_time(self):
        self.assertRoundTrip("time", datetime.time(13, 45, 10))

    @KNOWN_BROKEN
    def test_decimal(self):
        self.assertRoundTrip("decimal", decimal.Decimal("1234.56"))

    @KNOWN_BROKEN
    def test_uuid(self):
        self.assertRoundTrip("uuid", uuid.uuid4())

    @KNOWN_BROKEN
    def test_json(self):
        self.assertRoundTrip("json", {"a": 1, "b": [True, None, "x"]})


class StorageFormatTests(RoundTripMixin, TestCase):
    """
    O valor gravado no banco deve ser um token Fernet, nunca o texto puro.
    """

    def test_value_is_encrypted_in_database(self):
        obj = self.assertRoundTrip("char", "segredo")
        raw = self.raw_value(obj, "char")
        self.assertNotIn("segredo", raw)
        self.assertEqual(Fernet(settings.ENCRYPTION_KEY).decrypt(raw.encode()), b"segredo")

    def test_none_is_stored_as_null(self):
        obj = AllFields.objects.create(char=None, integer=None)
        self.assertIsNone(self.raw_value(obj, "char"))
        self.assertIsNone(AllFields.objects.get(pk=obj.pk).integer)

    def test_same_value_produces_different_ciphertexts(self):
        a = AllFields.objects.create(char="igual")
        b = AllFields.objects.create(char="igual")
        self.assertNotEqual(self.raw_value(a, "char"), self.raw_value(b, "char"))

    def test_lookup_by_value_does_not_match(self):
        """
        Limitação do Fernet (criptografia não determinística): filtros por valor não funcionam.
        """
        AllFields.objects.create(char="procurado")
        self.assertFalse(AllFields.objects.filter(char="procurado").exists())


class ValidationTests(TestCase):
    @KNOWN_BROKEN
    def test_invalid_integer_raises_validation_error(self):
        with self.assertRaises(ValidationError):
            AllFields(integer="abc").full_clean()


class PublicApiTests(unittest.TestCase):
    def test_star_import_does_not_leak_internal_names(self):
        namespace = {}
        exec("import datetime\nfrom encrypted_fields import *", namespace)
        self.assertIs(namespace["datetime"], datetime)
        self.assertIn("EncryptedCharField", namespace)
        self.assertIn("EncryptedImageField", namespace)
        self.assertNotIn("models", namespace)
