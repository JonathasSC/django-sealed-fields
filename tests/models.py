import uuid

from django.db import models

from sealed_fields import (
    EncryptedBooleanField,
    EncryptedCharField,
    EncryptedDateField,
    EncryptedDateTimeField,
    EncryptedDecimalField,
    EncryptedEmailField,
    EncryptedFileField,
    EncryptedFloatField,
    EncryptedImageField,
    EncryptedIntegerField,
    EncryptedJSONField,
    EncryptedTextField,
    EncryptedTimeField,
    EncryptedURLField,
    EncryptedUUIDField,
)


class AllFields(models.Model):
    integer = EncryptedIntegerField(null=True)
    float = EncryptedFloatField(null=True)
    boolean = EncryptedBooleanField(null=True)
    char = EncryptedCharField(max_length=100, null=True)
    text = EncryptedTextField(null=True)
    date = EncryptedDateField(null=True)
    datetime = EncryptedDateTimeField(null=True)
    time = EncryptedTimeField(null=True)
    decimal = EncryptedDecimalField(max_digits=10, decimal_places=2, null=True)
    email = EncryptedEmailField(null=True)
    url = EncryptedURLField(null=True)
    uuid = EncryptedUUIDField(null=True)
    json = EncryptedJSONField(null=True)


class Document(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, unique=True)
    title = models.CharField(max_length=50, blank=True)
    file = EncryptedFileField(upload_to="docs/", null=True, blank=True)
    image = EncryptedImageField(upload_to="imgs/", null=True, blank=True)
    plain = models.FileField(upload_to="plain/", null=True, blank=True)


class WithoutUUID(models.Model):
    file = EncryptedFileField(upload_to="docs/", null=True, blank=True)


class Photo(models.Model):
    image = EncryptedImageField(upload_to="photos/", width_field="width", height_field="height")
    width = models.PositiveIntegerField(null=True)
    height = models.PositiveIntegerField(null=True)
