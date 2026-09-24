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

    def test_datetime_aware(self):
        self.assertRoundTrip("datetime", timezone.now())

    def test_datetime_other_timezone_keeps_instant(self):
        value = datetime.datetime(2024, 1, 2, 3, 4, 5, 123456, tzinfo=datetime.timezone(datetime.timedelta(hours=-3)))
        obj = AllFields.objects.create(datetime=value)
        loaded = AllFields.objects.get(pk=obj.pk).datetime
        self.assertEqual(loaded, value)
        self.assertEqual(loaded.utcoffset(), datetime.timedelta(0))

    def test_datetime_without_microseconds(self):
        self.assertRoundTrip("datetime", datetime.datetime(2024, 1, 2, 3, 4, 5, tzinfo=datetime.timezone.utc))

    def test_time(self):
        self.assertRoundTrip("time", datetime.time(13, 45, 10))
        self.assertRoundTrip("time", datetime.time(1, 2, 3, 456))

    def test_decimal(self):
        self.assertRoundTrip("decimal", decimal.Decimal("1234.56"))
        self.assertRoundTrip("decimal", decimal.Decimal("-0.01"))

    def test_decimal_from_string(self):
        obj = AllFields.objects.create(decimal="10.50")
        self.assertEqual(AllFields.objects.get(pk=obj.pk).decimal, decimal.Decimal("10.50"))

    def test_uuid(self):
        self.assertRoundTrip("uuid", uuid.uuid4())

    def test_uuid_is_encrypted(self):
        value = uuid.uuid4()
        obj = self.assertRoundTrip("uuid", value)
        raw = self.raw_value(obj, "uuid")
        self.assertNotIn(value.hex, raw)
        self.assertNotIn(str(value), raw)

    def test_uuid_from_string(self):
        value = uuid.uuid4()
        obj = AllFields.objects.create(uuid=str(value))
        self.assertEqual(AllFields.objects.get(pk=obj.pk).uuid, value)

    def test_json(self):
        self.assertRoundTrip("json", {"a": 1, "b": [True, None, "x"], "c": {"d": 1.5}})
        self.assertRoundTrip("json", [1, "dois", {"três": 3}])
        self.assertRoundTrip("json", "texto")
        self.assertRoundTrip("json", 0)


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
    def assertInvalid(self, **kwargs):
        with self.assertRaises(ValidationError) as ctx:
            AllFields(**kwargs).full_clean()
        self.assertIn(next(iter(kwargs)), ctx.exception.message_dict)

    def test_invalid_values_raise_validation_error(self):
        self.assertInvalid(integer="abc")
        self.assertInvalid(float="abc")
        self.assertInvalid(date="2024-13-45")
        self.assertInvalid(datetime="ontem")
        self.assertInvalid(decimal="1234567890.123")
        self.assertInvalid(uuid="nao-e-uuid")
        self.assertInvalid(email="nao-e-email")
        self.assertInvalid(char="x" * 101)

    def test_valid_values_pass_validation(self):
        values = {"integer": 1, "date": datetime.date(2024, 1, 1), "email": "a@b.com", "uuid": uuid.uuid4()}
        others = [f.name for f in AllFields._meta.fields if f.name not in values]
        AllFields(**values).clean_fields(exclude=others)

    def test_integer_range_validator(self):
        self.assertInvalid(integer=2**31)


class LegacyDataTests(TestCase):
    """
    Valores gravados pela versão anterior do pacote continuam legíveis.
    """

    def insert_encrypted(self, **plaintexts):
        fernet = Fernet(settings.ENCRYPTION_KEY)
        obj = AllFields.objects.create()
        with connection.cursor() as cursor:
            for column, plaintext in plaintexts.items():
                cursor.execute(
                    f"UPDATE {AllFields._meta.db_table} SET {column} = %s WHERE id = %s",
                    [fernet.encrypt(plaintext.encode()).decode(), obj.pk],
                )
        return AllFields.objects.get(pk=obj.pk)

    def test_legacy_formats(self):
        obj = self.insert_encrypted(
            integer="42",
            float="1.5",
            boolean="False",
            char="texto",
            date="2024-01-02",
            datetime="2024-01-02 03:04:05+00:00",
            time="13:45:10",
            decimal="12.34",
        )
        self.assertEqual(obj.integer, 42)
        self.assertEqual(obj.float, 1.5)
        self.assertIs(obj.boolean, False)
        self.assertEqual(obj.char, "texto")
        self.assertEqual(obj.date, datetime.date(2024, 1, 2))
        self.assertEqual(obj.datetime, datetime.datetime(2024, 1, 2, 3, 4, 5, tzinfo=datetime.timezone.utc))
        self.assertEqual(obj.time, datetime.time(13, 45, 10))
        self.assertEqual(obj.decimal, decimal.Decimal("12.34"))


class PublicApiTests(unittest.TestCase):
    def test_star_import_does_not_leak_internal_names(self):
        namespace = {}
        exec("import datetime\nfrom encrypted_fields import *", namespace)
        self.assertIs(namespace["datetime"], datetime)
        self.assertIn("EncryptedCharField", namespace)
        self.assertIn("EncryptedImageField", namespace)
        self.assertNotIn("models", namespace)


class WritePathsTests(TestCase):
    """
    Todos os caminhos de escrita do ORM devem gravar o valor criptografado.
    """

    def raw_values(self, column):
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT {column} FROM {AllFields._meta.db_table} ORDER BY id")
            return [row[0] for row in cursor.fetchall()]

    def assertAllEncrypted(self, column, plaintext):
        fernet = Fernet(settings.ENCRYPTION_KEY)
        for raw in self.raw_values(column):
            self.assertNotIn(plaintext, raw)
            self.assertEqual(fernet.decrypt(raw.encode()).decode(), plaintext)

    def test_queryset_update(self):
        AllFields.objects.create(char="antigo", decimal=decimal.Decimal("1.00"))
        AllFields.objects.update(char="novo valor", decimal=decimal.Decimal("9.99"))
        self.assertAllEncrypted("char", "novo valor")
        self.assertAllEncrypted("decimal", "9.99")
        self.assertEqual(AllFields.objects.get().decimal, decimal.Decimal("9.99"))

    def test_bulk_create(self):
        AllFields.objects.bulk_create([AllFields(char="lote"), AllFields(char="lote")])
        self.assertAllEncrypted("char", "lote")

    def test_bulk_update(self):
        objs = AllFields.objects.bulk_create([AllFields(char="a"), AllFields(char="b")])
        for obj in objs:
            obj.char = "atualizado"
        AllFields.objects.bulk_update(objs, ["char"])
        self.assertAllEncrypted("char", "atualizado")
        self.assertEqual(list(AllFields.objects.values_list("char", flat=True)), ["atualizado"] * 2)

    def test_values_list_decrypts(self):
        AllFields.objects.create(integer=7, json={"k": "v"})
        self.assertEqual(list(AllFields.objects.values_list("integer", "json")), [(7, {"k": "v"})])

    def test_serializers_round_trip(self):
        from django.core import serializers

        original = AllFields.objects.create(
            integer=1,
            # O serializador JSON do Django trunca microssegundos, como em um DateTimeField comum
            datetime=timezone.now().replace(microsecond=0),
            decimal=decimal.Decimal("2.50"),
            uuid=uuid.uuid4(),
            json={"a": [1, 2]},
        )
        data = serializers.serialize("json", AllFields.objects.all())
        AllFields.objects.all().delete()
        for deserialized in serializers.deserialize("json", data):
            deserialized.save()
        loaded = AllFields.objects.get(pk=original.pk)
        for field in ("integer", "datetime", "decimal", "uuid", "json"):
            self.assertEqual(getattr(loaded, field), getattr(original, field), field)
