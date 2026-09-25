import io
import os
import shutil
import tempfile
from unittest import mock

from cryptography.fernet import Fernet
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import TestCase, override_settings
from PIL import Image

from .models import Document, Photo


def png_bytes(color="red"):
    buffer = io.BytesIO()
    Image.new("RGB", (4, 4), color).save(buffer, "PNG")
    return buffer.getvalue()


class MediaRootMixin:
    def setUp(self):
        super().setUp()
        self.media_root = tempfile.mkdtemp(prefix="sealed-fields-media-")
        override = override_settings(MEDIA_ROOT=self.media_root)
        override.enable()
        self.addCleanup(override.disable)
        self.addCleanup(shutil.rmtree, self.media_root, ignore_errors=True)

    def files_in(self, directory):
        path = os.path.join(self.media_root, directory)
        return sorted(os.listdir(path)) if os.path.isdir(path) else []

    def raw_bytes(self, name):
        with open(os.path.join(self.media_root, name), "rb") as f:
            return f.read()

    def stored_name(self, obj, field_name):
        """
        Valor gravado na coluna, sem passar pelo from_db_value do campo.
        """
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT {field_name} FROM {Document._meta.db_table} WHERE id = %s", [obj.pk])
            return cursor.fetchone()[0]


class EncryptedFileFieldTests(MediaRootMixin, TestCase):
    def test_create_encrypts_content_on_disk(self):
        obj = Document.objects.create(file=ContentFile(b"conteudo secreto", name="a.txt"))
        name = self.stored_name(obj, "file")
        self.assertEqual(name, "docs/a.txt")
        raw = self.raw_bytes(name)
        self.assertNotIn(b"conteudo secreto", raw)
        self.assertEqual(Fernet(settings.ENCRYPTION_KEY).decrypt(raw), b"conteudo secreto")

    def test_load_decrypts_content(self):
        obj = Document.objects.create(file=ContentFile(b"conteudo", name="a.txt"))
        loaded = Document.objects.get(pk=obj.pk)
        self.assertEqual(loaded.file.read(), b"conteudo")

    def test_loaded_name_is_relative_to_storage(self):
        obj = Document.objects.create(file=ContentFile(b"x", name="a.txt"))
        loaded = Document.objects.get(pk=obj.pk)
        self.assertEqual(loaded.file.name, "docs/a.txt")

    def test_uploaded_file(self):
        upload = SimpleUploadedFile("relatorio.pdf", b"%PDF-1.4 dados", content_type="application/pdf")
        obj = Document.objects.create(file=upload)
        self.assertEqual(Document.objects.get(pk=obj.pk).file.read(), b"%PDF-1.4 dados")

    def test_resave_does_not_duplicate_file(self):
        obj = Document.objects.create(file=ContentFile(b"conteudo", name="a.txt"))
        for title in ("um", "dois"):
            loaded = Document.objects.get(pk=obj.pk)
            loaded.title = title
            loaded.save()
        self.assertEqual(self.files_in("docs"), ["a.txt"])
        self.assertEqual(self.stored_name(obj, "file"), "docs/a.txt")
        self.assertEqual(Document.objects.get(pk=obj.pk).file.read(), b"conteudo")

    def test_resave_with_update_fields_does_not_duplicate_file(self):
        obj = Document.objects.create(file=ContentFile(b"conteudo", name="a.txt"))
        loaded = Document.objects.get(pk=obj.pk)
        loaded.title = "novo"
        loaded.save(update_fields=["title", "file"])
        self.assertEqual(self.files_in("docs"), ["a.txt"])

    def test_resave_same_instance_after_create(self):
        obj = Document.objects.create(file=ContentFile(b"conteudo", name="a.txt"))
        obj.title = "novo"
        obj.save()
        self.assertEqual(self.files_in("docs"), ["a.txt"])
        self.assertEqual(Document.objects.get(pk=obj.pk).file.read(), b"conteudo")

    def test_replacing_file_encrypts_new_content(self):
        obj = Document.objects.create(file=ContentFile(b"antigo", name="a.txt"))
        loaded = Document.objects.get(pk=obj.pk)
        loaded.file = ContentFile(b"novo", name="b.txt")
        loaded.save()
        reloaded = Document.objects.get(pk=obj.pk)
        self.assertEqual(reloaded.file.name, "docs/b.txt")
        self.assertEqual(reloaded.file.read(), b"novo")
        self.assertNotIn(b"novo", self.raw_bytes("docs/b.txt"))

    def test_upload_name_directories_are_stripped(self):
        obj = Document.objects.create(file=ContentFile(b"x", name="../../fora/a.txt"))
        self.assertEqual(self.stored_name(obj, "file"), "docs/a.txt")

    def test_empty_file_is_stored_as_null(self):
        obj = Document.objects.create(file=ContentFile(b"", name="vazio.txt"))
        self.assertIn(self.stored_name(obj, "file"), (None, ""))
        self.assertFalse(Document.objects.get(pk=obj.pk).file)

    def test_without_file(self):
        obj = Document.objects.create(title="sem arquivo")
        self.assertFalse(Document.objects.get(pk=obj.pk).file)

    def test_missing_file_does_not_break_queries(self):
        Document.objects.create(file=ContentFile(b"x", name="a.txt"))
        default_storage.delete("docs/a.txt")
        documents = list(Document.objects.all())
        self.assertEqual(documents[0].file.name, "docs/a.txt")
        with self.assertRaises(FileNotFoundError):
            documents[0].file.read()

    def test_loading_does_not_read_storage(self):
        Document.objects.create(file=ContentFile(b"x", name="a.txt"), image=ContentFile(png_bytes(), name="f.png"))
        with mock.patch.object(default_storage, "open", side_effect=AssertionError("leu o storage")):
            documents = list(Document.objects.all())
            self.assertEqual(Document.objects.values_list("file", flat=True).get(), "docs/a.txt")
        self.assertEqual(documents[0].file.read(), b"x")

    def test_content_available_right_after_create(self):
        obj = Document.objects.create(file=ContentFile(b"conteudo", name="a.txt"))
        self.assertEqual(obj.file.read(), b"conteudo")

    def test_open_as_context_manager_and_chunks(self):
        obj = Document.objects.create(file=ContentFile(b"abc" * 1000, name="a.txt"))
        loaded = Document.objects.get(pk=obj.pk)
        with loaded.file.open("rb") as f:
            self.assertEqual(b"".join(f.chunks(chunk_size=100)), b"abc" * 1000)
        with loaded.file.open("rb") as f:
            self.assertEqual(f.read(3), b"abc")

    def test_save_through_field_file(self):
        obj = Document.objects.create(title="x")
        obj.file.save("novo.txt", ContentFile(b"via FieldFile.save"))
        self.assertEqual(self.stored_name(obj, "file"), "docs/novo.txt")
        self.assertNotIn(b"via FieldFile.save", self.raw_bytes("docs/novo.txt"))
        self.assertEqual(Document.objects.get(pk=obj.pk).file.read(), b"via FieldFile.save")

    def test_size_is_decrypted_size(self):
        obj = Document.objects.create(file=ContentFile(b"x" * 1000, name="a.txt"))
        self.assertEqual(Document.objects.get(pk=obj.pk).file.size, 1000)
        self.assertGreater(default_storage.size("docs/a.txt"), 1000)

    def test_text_content(self):
        obj = Document.objects.create(file=ContentFile("texto com acentuação", name="a.txt"))
        self.assertEqual(Document.objects.get(pk=obj.pk).file.read(), "texto com acentuação".encode())

    def test_delete_removes_file_from_storage(self):
        obj = Document.objects.create(file=ContentFile(b"x", name="a.txt"))
        Document.objects.get(pk=obj.pk).file.delete(save=False)
        self.assertEqual(self.files_in("docs"), [])

    def test_url_points_to_stored_file(self):
        obj = Document.objects.create(file=ContentFile(b"x", name="a.txt"))
        self.assertTrue(Document.objects.get(pk=obj.pk).file.url.endswith("docs/a.txt"))


class EncryptedImageFieldTests(MediaRootMixin, TestCase):
    def test_image_round_trip(self):
        content = png_bytes()
        obj = Document.objects.create(image=ContentFile(content, name="foto.png"))
        self.assertNotEqual(self.raw_bytes("imgs/foto.png"), content)
        self.assertEqual(Document.objects.get(pk=obj.pk).image.read(), content)

    def test_resave_does_not_duplicate_image(self):
        obj = Document.objects.create(image=ContentFile(png_bytes(), name="foto.png"))
        loaded = Document.objects.get(pk=obj.pk)
        loaded.title = "novo"
        loaded.save()
        self.assertEqual(self.files_in("imgs"), ["foto.png"])

    def test_image_dimensions_use_decrypted_content(self):
        buffer = io.BytesIO()
        Image.new("RGB", (7, 3)).save(buffer, "PNG")
        photo = Photo.objects.create(image=ContentFile(buffer.getvalue(), name="p.png"))
        self.assertEqual((photo.width, photo.height), (7, 3))
        loaded = Photo.objects.get(pk=photo.pk)
        self.assertEqual((loaded.width, loaded.height), (7, 3))
        self.assertEqual((loaded.image.width, loaded.image.height), (7, 3))

    def test_existing_encrypted_file_is_readable(self):
        """
        Arquivos gravados pela versão anterior (mesmo formato Fernet) continuam legíveis.
        """
        content = png_bytes("blue")
        name = default_storage.save("imgs/antiga.png", ContentFile(Fernet(settings.ENCRYPTION_KEY).encrypt(content)))
        Document.objects.bulk_create([Document(title="x")])
        Document.objects.update(image=name)
        self.assertEqual(Document.objects.get().image.read(), content)
