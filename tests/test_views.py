from unittest import mock

from django.contrib.auth.models import Permission, User
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.test import TestCase, override_settings

from sealed_fields.serve.views import get_file_url, get_file_url_with_timestamp

from .models import Document
from .test_files import MediaRootMixin, png_bytes


class ServeDecryptedFileTests(MediaRootMixin, TestCase):
    def setUp(self):
        super().setUp()
        cache.clear()
        self.addCleanup(cache.clear)
        self.document = Document.objects.create(
            title="doc",
            file=ContentFile(b"conteudo secreto", name="relatório.txt"),
            image=ContentFile(png_bytes(), name="foto.png"),
            plain=ContentFile(b"texto puro", name="plain.txt"),
        )
        self.user = User.objects.create_user("comum", password="x")
        self.viewer = User.objects.create_user("leitor", password="x")
        self.viewer.user_permissions.add(Permission.objects.get(codename="view_document"))

    def url(self, field="file", model="Document", app="tests", uuid=None):
        return get_file_url(app, model, field, uuid or self.document.uuid)

    # Autenticação e permissão

    def test_anonymous_is_redirected_to_login(self):
        response = self.client.get(self.url())
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response["Location"])
        self.assertNotIn(b"conteudo secreto", response.content)

    def test_user_without_permission_is_forbidden(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url())
        self.assertEqual(response.status_code, 403)
        self.assertNotIn(b"conteudo secreto", response.content)

    def test_user_with_view_permission_gets_decrypted_file(self):
        self.client.force_login(self.viewer)
        response = self.client.get(self.url())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"conteudo secreto")
        self.assertEqual(response["Content-Type"], "text/plain")

    def test_superuser_gets_file(self):
        self.client.force_login(User.objects.create_superuser("admin", password="x"))
        self.assertEqual(self.client.get(self.url()).status_code, 200)

    @override_settings(SERVE_DECRYPTED_FILE_PERMISSION_CHECK="tests.permissions.allow_title_publico")
    def test_custom_permission_check(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(self.url()).status_code, 403)
        Document.objects.filter(pk=self.document.pk).update(title="publico")
        self.assertEqual(self.client.get(self.url()).status_code, 200)

    def test_cached_response_still_checks_permission(self):
        self.client.force_login(self.viewer)
        self.assertEqual(self.client.get(self.url()).status_code, 200)
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(self.url()).status_code, 403)

    # Conteúdo e cabeçalhos

    def test_image_is_served_decrypted(self):
        self.client.force_login(self.viewer)
        response = self.client.get(self.url(field="image"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/png")
        self.assertEqual(response.content, png_bytes())

    def test_plain_file_field_is_served(self):
        self.client.force_login(self.viewer)
        response = self.client.get(self.url(field="plain"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"texto puro")

    def test_headers(self):
        self.client.force_login(self.viewer)
        response = self.client.get(self.url())
        self.assertEqual(response["Content-Disposition"], "inline; filename*=utf-8''relat%C3%B3rio.txt")
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
        self.assertEqual(response["Cache-Control"], "no-cache, no-store, must-revalidate")
        self.assertNotIn("ETag", response)

    def test_timestamp_url_sets_etag(self):
        self.client.force_login(self.viewer)
        url = get_file_url_with_timestamp("tests", "Document", "file", self.document.uuid, 1700000000)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["ETag"], '"1700000000"')

    def test_response_is_cached(self):
        self.client.force_login(self.viewer)
        self.client.get(self.url())
        with mock.patch("sealed_fields.files.EncryptedFileFieldMixin.from_db_value") as from_db:
            from_db.side_effect = AssertionError("não deveria descriptografar de novo")
            response = self.client.get(self.url())
        self.assertEqual(response.content, b"conteudo secreto")

    # Entradas inválidas

    def test_unknown_app_or_model_returns_404(self):
        self.client.force_login(self.viewer)
        self.assertEqual(self.client.get(self.url(app="inexistente")).status_code, 404)
        self.assertEqual(self.client.get(self.url(model="Inexistente")).status_code, 404)

    def test_unknown_field_returns_404(self):
        self.client.force_login(self.viewer)
        self.assertEqual(self.client.get(self.url(field="inexistente")).status_code, 404)

    def test_non_file_field_returns_404(self):
        self.client.force_login(self.viewer)
        self.assertEqual(self.client.get(self.url(field="title")).status_code, 404)

    def test_model_attribute_that_is_not_a_field_returns_404(self):
        self.client.force_login(self.viewer)
        self.assertEqual(self.client.get(self.url(field="save")).status_code, 404)

    def test_model_from_other_app_is_not_exposed_without_permission(self):
        self.client.force_login(self.viewer)
        response = self.client.get(self.url(app="auth", model="User", field="password"))
        self.assertEqual(response.status_code, 404)

    def test_unknown_uuid_returns_404(self):
        self.client.force_login(self.viewer)
        response = self.client.get(self.url(uuid="00000000-0000-0000-0000-000000000000"))
        self.assertEqual(response.status_code, 404)

    def test_invalid_uuid_returns_404(self):
        self.client.force_login(self.viewer)
        self.assertEqual(self.client.get(self.url(uuid="nao-e-uuid")).status_code, 404)

    def test_model_without_uuid_returns_404(self):
        self.client.force_login(User.objects.create_superuser("admin", password="x"))
        self.assertEqual(self.client.get(self.url(model="WithoutUUID")).status_code, 404)

    def test_empty_file_field_returns_404(self):
        self.client.force_login(self.viewer)
        empty = Document.objects.create(title="vazio")
        self.assertEqual(self.client.get(self.url(uuid=empty.uuid)).status_code, 404)

    def test_internal_error_does_not_leak_details(self):
        self.client.force_login(self.viewer)
        with (
            mock.patch("sealed_fields.serve.views.guess_type", side_effect=RuntimeError("detalhe interno")),
            self.assertLogs("sealed_fields.serve.views", "ERROR"),
        ):
            response = self.client.get(self.url())
        self.assertEqual(response.status_code, 500)
        self.assertNotIn(b"detalhe interno", response.content)
