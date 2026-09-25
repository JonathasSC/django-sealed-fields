import datetime
import json

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.backends.base.operations import BaseDatabaseOperations
from django.utils.functional import cached_property

from .field_mixin import EncryptedFieldMixin

__all__ = [
    "EncryptedBooleanField",
    "EncryptedCharField",
    "EncryptedDateField",
    "EncryptedDateTimeField",
    "EncryptedDecimalField",
    "EncryptedEmailField",
    "EncryptedFloatField",
    "EncryptedIntegerField",
    "EncryptedJSONField",
    "EncryptedTextField",
    "EncryptedTimeField",
    "EncryptedURLField",
    "EncryptedUUIDField",
]


class EncryptedIntegerField(EncryptedFieldMixin, models.IntegerField):
    """
    Campo criptografado para valores inteiros.
    """

    @cached_property
    def validators(self) -> list[MinValueValidator | MaxValueValidator]:
        # These validators can't be added at field initialization time since
        # they're based on values retrieved from `connection`.
        validators_ = [*self.default_validators, *self._validators]
        internal_type = models.IntegerField().get_internal_type()
        min_value, max_value = BaseDatabaseOperations.integer_field_ranges[internal_type]
        if min_value is not None and not any(
            (
                isinstance(validator, MinValueValidator)
                and (validator.limit_value() if callable(validator.limit_value) else validator.limit_value) >= min_value
            )
            for validator in validators_
        ):
            validators_.append(MinValueValidator(min_value))
        if max_value is not None and not any(
            (
                isinstance(validator, MaxValueValidator)
                and (validator.limit_value() if callable(validator.limit_value) else validator.limit_value) <= max_value
            )
            for validator in validators_
        ):
            validators_.append(MaxValueValidator(max_value))
        return validators_


class EncryptedFloatField(EncryptedFieldMixin, models.FloatField):
    """
    Campo criptografado para valores flutuantes (float).
    """


class EncryptedBooleanField(EncryptedFieldMixin, models.BooleanField):
    """
    Campo criptografado para valores booleanos.
    """


class EncryptedCharField(EncryptedFieldMixin, models.CharField):
    """
    Campo criptografado para strings.
    """


class EncryptedTextField(EncryptedFieldMixin, models.TextField):
    """
    Campo criptografado para strings.
    """


class EncryptedDateField(EncryptedFieldMixin, models.DateField):
    """
    Campo criptografado para datas.
    """


class EncryptedDateTimeField(EncryptedFieldMixin, models.DateTimeField):
    """
    Campo criptografado para valores de data e hora.
    """

    def serialize_value(self, value):
        # Valores com fuso horário são gravados em UTC, como o Django faz nas colunas nativas
        if value.tzinfo is not None:
            value = value.astimezone(datetime.timezone.utc)
        return value.isoformat()


class EncryptedTimeField(EncryptedFieldMixin, models.TimeField):
    """
    Campo criptografado para valores de hora.
    """


class EncryptedDecimalField(EncryptedFieldMixin, models.DecimalField):
    """
    Campo criptografado para valores decimais.
    """


class EncryptedEmailField(EncryptedFieldMixin, models.EmailField):
    """
    Campo criptografado para endereços de e-mail.
    """


class EncryptedURLField(EncryptedFieldMixin, models.URLField):
    """
    Campo criptografado para URLs.
    """


class EncryptedUUIDField(EncryptedFieldMixin, models.UUIDField):
    """
    Campo criptografado para valores UUID.
    """


class EncryptedJSONField(EncryptedFieldMixin, models.JSONField):
    """
    Campo criptografado para valores JSON.
    """

    def serialize_value(self, value):
        return json.dumps(value, cls=self.encoder)

    def cast_value(self, value):
        return json.loads(value, cls=self.decoder)
