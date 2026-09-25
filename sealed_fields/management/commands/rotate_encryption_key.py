from cryptography.fernet import InvalidToken
from django.apps import apps
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import models, transaction
from django.db.models.functions import Cast

from sealed_fields.crypto import get_cipher, get_keys, get_primary_cipher
from sealed_fields.field_mixin import EncryptedFieldMixin
from sealed_fields.files import EncryptedFileFieldMixin


class Command(BaseCommand):
    help = (
        "Recriptografa campos e arquivos criptografados com a chave principal "
        "(a primeira de ENCRYPTION_KEY). Valores que já usam a chave principal são ignorados, "
        "então o comando pode ser interrompido e executado novamente."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "models",
            nargs="*",
            metavar="app_label[.ModelName]",
            help="Limita a rotação a estes apps ou modelos. Por padrão, todos.",
        )
        parser.add_argument("--dry-run", action="store_true", help="Apenas conta o que seria recriptografado.")
        parser.add_argument("--batch-size", type=int, default=500, help="Linhas por transação (padrão: 500).")

    def handle(self, *args, **options):
        if len(get_keys()) < 2:
            self.stdout.write(
                self.style.WARNING(
                    "ENCRYPTION_KEY tem apenas uma chave. Para rotacionar, use [nova_chave, chave_antiga]."
                )
            )

        self.dry_run = options["dry_run"]
        self.batch_size = options["batch_size"]
        self.cipher = get_cipher()
        self.primary = get_primary_cipher()

        total = 0
        for model in self.get_models(options["models"]):
            value_fields = [f for f in model._meta.concrete_fields if isinstance(f, EncryptedFieldMixin)]
            file_fields = [f for f in model._meta.concrete_fields if isinstance(f, EncryptedFileFieldMixin)]
            for field in value_fields:
                total += self.report(model, field, self.rotate_values(model, field))
            for field in file_fields:
                total += self.report(model, field, self.rotate_files(model, field))

        action = "seriam recriptografados" if self.dry_run else "recriptografados"
        self.stdout.write(self.style.SUCCESS(f"Concluído: {total} valores/arquivos {action}."))

    def get_models(self, labels):
        if not labels:
            return [m for m in apps.get_models() if not m._meta.proxy]
        selected = []
        for label in labels:
            try:
                if "." in label:
                    selected.append(apps.get_model(label))
                else:
                    selected.extend(m for m in apps.get_app_config(label).get_models() if not m._meta.proxy)
            except LookupError as e:
                raise CommandError(str(e)) from e
        return selected

    def report(self, model, field, result):
        rotated, skipped, missing = result
        if rotated or skipped or missing:
            line = f"{model._meta.label}.{field.name}: {rotated} recriptografados, {skipped} já atualizados"
            if missing:
                line += f", {missing} arquivos ausentes"
            self.stdout.write(line)
        return rotated

    def needs_rotation(self, token):
        try:
            self.primary.decrypt(token)
        except InvalidToken:
            return True
        return False

    def iterate(self, model, *fields):
        """
        Percorre a tabela em lotes ordenados pela chave primária.
        """
        queryset = model._base_manager.order_by("pk")
        last_pk = None
        while True:
            batch = queryset if last_pk is None else queryset.filter(pk__gt=last_pk)
            rows = list(batch.values_list("pk", *fields)[: self.batch_size])
            if not rows:
                return
            yield rows
            last_pk = rows[-1][0]

    def rotate_values(self, model, field):
        rotated = skipped = 0
        # Cast para texto: lê o token cru, sem passar pela descriptografia do campo
        raw = Cast(field.name, output_field=models.TextField())
        for rows in self.iterate(model, raw):
            with transaction.atomic(using=model._base_manager.db):
                for pk, token in rows:
                    if token is None:
                        continue
                    if not self.needs_rotation(token.encode()):
                        skipped += 1
                        continue
                    rotated += 1
                    if not self.dry_run:
                        new_token = self.cipher.rotate(token.encode()).decode()
                        model._base_manager.filter(pk=pk).update(
                            **{field.name: models.Value(new_token, output_field=models.TextField())}
                        )
        return rotated, skipped, 0

    def rotate_files(self, model, field):
        rotated = skipped = missing = 0
        storage = field.storage
        for rows in self.iterate(model, field.name):
            for pk, name in rows:
                if not name:
                    continue
                if not storage.exists(name):
                    missing += 1
                    self.stderr.write(f"Arquivo ausente: {name} ({model._meta.label} pk={pk})")
                    continue
                with storage.open(name, "rb") as f:
                    token = f.read()
                if not self.needs_rotation(token):
                    skipped += 1
                    continue
                rotated += 1
                if self.dry_run:
                    continue
                # Grava a nova versão antes de apagar a antiga: uma falha no meio nunca perde o arquivo
                new_name = storage.save(name, ContentFile(self.cipher.rotate(token)), max_length=field.max_length)
                if new_name != name:
                    model._base_manager.filter(pk=pk).update(**{field.name: new_name})
                    storage.delete(name)
                # Storages que sobrescrevem (como S3 com file_overwrite) gravam no mesmo nome: nada a apagar
        return rotated, skipped, missing
