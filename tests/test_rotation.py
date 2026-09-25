import io

from cryptography.fernet import Fernet, InvalidToken
from django.core.exceptions import ImproperlyConfigured
from django.core.files.base import ContentFile
from django.core.management import CommandError, call_command
from django.db import connection
from django.test import TestCase, override_settings

from .models import AllFields, Document, OverwriteDocument
from .test_files import MediaRootMixin, png_bytes

OLD_KEY = Fernet.generate_key()
NEW_KEY = Fernet.generate_key()


def raw_column(model, column, pk):
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT {column} FROM {model._meta.db_table} WHERE id = %s", [pk])
        return cursor.fetchone()[0]


class KeyConfigurationTests(TestCase):
    @override_settings(ENCRYPTION_KEY=OLD_KEY.decode())
    def test_key_as_string(self):
        obj = AllFields.objects.create(char="texto")
        self.assertEqual(AllFields.objects.get(pk=obj.pk).char, "texto")
        self.assertEqual(Fernet(OLD_KEY).decrypt(raw_column(AllFields, "char", obj.pk).encode()), b"texto")

    def test_first_key_encrypts_and_all_keys_decrypt(self):
        with override_settings(ENCRYPTION_KEY=OLD_KEY):
            old = AllFields.objects.create(char="antigo")
        with override_settings(ENCRYPTION_KEY=[NEW_KEY, OLD_KEY]):
            new = AllFields.objects.create(char="novo")
            self.assertEqual(AllFields.objects.get(pk=old.pk).char, "antigo")
            self.assertEqual(AllFields.objects.get(pk=new.pk).char, "novo")
        self.assertEqual(Fernet(NEW_KEY).decrypt(raw_column(AllFields, "char", new.pk).encode()), b"novo")

    def test_key_change_takes_effect_without_restart(self):
        with override_settings(ENCRYPTION_KEY=OLD_KEY):
            obj = AllFields.objects.create(char="x")
        with override_settings(ENCRYPTION_KEY=NEW_KEY), self.assertRaises(InvalidToken):
            AllFields.objects.get(pk=obj.pk)

    @override_settings(ENCRYPTION_KEY=None)
    def test_missing_key(self):
        with self.assertRaisesMessage(ImproperlyConfigured, "ENCRYPTION_KEY must be set"):
            AllFields.objects.create(char="x")

    @override_settings(ENCRYPTION_KEY="chave-invalida")
    def test_invalid_key(self):
        with self.assertRaisesMessage(ImproperlyConfigured, "chave Fernet inválida"):
            AllFields.objects.create(char="x")


class RotateEncryptionKeyTests(MediaRootMixin, TestCase):
    def setUp(self):
        super().setUp()
        with override_settings(ENCRYPTION_KEY=OLD_KEY):
            self.values = AllFields.objects.create(char="segredo", integer=42, json={"a": [1, 2]})
            self.empty = AllFields.objects.create()
            self.document = Document.objects.create(
                file=ContentFile(b"conteudo", name="a.txt"),
                image=ContentFile(png_bytes(), name="foto.png"),
            )

    def rotate(self, *args):
        out = io.StringIO()
        with override_settings(ENCRYPTION_KEY=[NEW_KEY, OLD_KEY]):
            call_command("rotate_encryption_key", *args, stdout=out, stderr=io.StringIO())
        return out.getvalue()

    def test_values_and_files_are_readable_with_only_the_new_key(self):
        output = self.rotate()
        self.assertIn("Concluído: 5 valores/arquivos recriptografados.", output)
        with override_settings(ENCRYPTION_KEY=NEW_KEY):
            values = AllFields.objects.get(pk=self.values.pk)
            self.assertEqual((values.char, values.integer, values.json), ("segredo", 42, {"a": [1, 2]}))
            self.assertIsNone(AllFields.objects.get(pk=self.empty.pk).char)
            document = Document.objects.get(pk=self.document.pk)
            self.assertEqual(document.file.read(), b"conteudo")
            self.assertEqual(document.image.read(), png_bytes())

    def test_old_files_are_replaced(self):
        self.rotate()
        document = Document.objects.get(pk=self.document.pk)
        self.assertEqual(self.files_in("docs"), [document.file.name.split("/")[-1]])
        self.assertNotEqual(document.file.name, "docs/a.txt")

    def test_second_run_skips_rotated_values(self):
        self.rotate()
        output = self.rotate()
        self.assertIn("Concluído: 0 valores/arquivos recriptografados.", output)
        self.assertIn("tests.AllFields.char: 0 recriptografados, 1 já atualizados", output)

    def test_dry_run_changes_nothing(self):
        raw_before = raw_column(AllFields, "char", self.values.pk)
        output = self.rotate("--dry-run")
        self.assertIn("Concluído: 5 valores/arquivos seriam recriptografados.", output)
        self.assertEqual(raw_column(AllFields, "char", self.values.pk), raw_before)
        self.assertEqual(self.files_in("docs"), ["a.txt"])

    def test_limit_to_model(self):
        self.rotate("tests.Document")
        with override_settings(ENCRYPTION_KEY=NEW_KEY):
            self.assertEqual(Document.objects.get(pk=self.document.pk).file.read(), b"conteudo")
            with self.assertRaises(InvalidToken):
                AllFields.objects.get(pk=self.values.pk)

    def test_unknown_model(self):
        with self.assertRaises(CommandError):
            self.rotate("tests.Inexistente")

    def test_missing_file_is_reported_and_skipped(self):
        Document.objects.filter(pk=self.document.pk).update(file="docs/sumiu.txt")
        output = self.rotate("tests.Document")
        self.assertIn("1 arquivos ausentes", output)

    def test_overwriting_storage_keeps_the_file(self):
        with override_settings(ENCRYPTION_KEY=OLD_KEY):
            obj = OverwriteDocument.objects.create(file=ContentFile(b"sobrescrito", name="o.txt"))
        self.rotate("tests.OverwriteDocument")
        self.assertEqual(self.files_in("overwrite"), ["o.txt"])
        with override_settings(ENCRYPTION_KEY=NEW_KEY):
            self.assertEqual(OverwriteDocument.objects.get(pk=obj.pk).file.read(), b"sobrescrito")

    def test_single_key_warns(self):
        out = io.StringIO()
        with override_settings(ENCRYPTION_KEY=OLD_KEY):
            call_command("rotate_encryption_key", "--dry-run", stdout=out)
        self.assertIn("apenas uma chave", out.getvalue())
