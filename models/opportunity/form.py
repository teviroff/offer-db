from typing import Any, Callable, Generator, Self
from abc import abstractmethod
import re

import mongoengine as mongo

from ...utils import *
from ...serializers import mod as ser
from . import opportunity as _opportunity


class SubmitMethod(mongo.EmbeddedDocument):
    meta = {'allow_inheritance': True, 'abstract': True}

class NoopSubmitMethod(SubmitMethod):
    @classmethod
    def create(cls, _data: ser.OpportunityForm.NoopSubmitMethod) -> Self:
        return NoopSubmitMethod()

class YandexFormsSubmitMethod(SubmitMethod):
    url = mongo.URLField()

    @classmethod
    def create(cls, data: ser.OpportunityForm.YandexFormsSubmitMethod) -> Self:
        return YandexFormsSubmitMethod(url=str(data.url))


class FieldErrorCode(IntEnum):
    MISSING = 100
    EXTRA = 101
    WRONG_TYPE = 102
    LENGTH_NOT_IN_RANGE = 103
    INVALID_PATTERN = 104
    INVALID_CHOICE = 105

type FieldError = GenericError[FieldErrorCode, dict[str, Any]]


class FormField(mongo.EmbeddedDocument):
    meta = {'allow_inheritance': True, 'abstract': True}

    label = mongo.StringField()
    is_required = mongo.BooleanField()

    @abstractmethod
    def validate_input(self, field_name: str, input: Any) -> None | FieldError: ...


class StringField(FormField):
    max_length = mongo.IntField()

    @classmethod
    def create(cls, data: ser.OpportunityForm.StringField) -> Self:
        return StringField(label=data.label, is_required=data.is_required, max_length=data.max_length)

    def validate_input(self, field_name: str, input: Any) -> None | FieldError:
        if not isinstance(input, str):
            return GenericError(
                error_code=FieldErrorCode.WRONG_TYPE,
                error_message='Field input must be a string',
                context={'field_name': field_name},
            )
        if self.max_length and len(input) > self.max_length:
            return GenericError(
                error_code=FieldErrorCode.LENGTH_NOT_IN_RANGE,
                error_message=f'Field input can contain at most {self.max_length} symbols',
                context={'field_name': field_name},
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            'label': self.label,
            'is_requred': self.is_required,
            'max_length': self.max_length,
        }


class RegexField(StringField):
    regex = mongo.StringField()

    @classmethod
    def create(cls, data: ser.OpportunityForm.RegexField) -> Self:
        return RegexField(label=data.label, is_required=data.is_required, max_length=data.max_length, regex=data.regex)

    def validate_input(self, field_name: str, input: Any) -> None | FieldError:
        if error := super().validate_input(field_name, input):
            return error
        if not re.match(self.regex, input):
            return GenericError(
                error_code=FieldErrorCode.INVALID_PATTERN,
                error_message='Field input doesn\'t match expected pattern',
                context={'field_name': field_name},
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            'label': self.label,
            'is_requred': self.is_required,
            'max_length': self.max_length,
            'regex': self.regex,
        }


class ChoiceField(FormField):
    choices = mongo.ListField(mongo.StringField())

    @classmethod
    def create(cls, data: ser.OpportunityForm.ChoiceField) -> Self:
        return ChoiceField(label=data.label, is_required=data.is_required, choices=data.choices)

    def validate_input(self, field_name: str, input: Any) -> None | FieldError:
        if not isinstance(input, str):
            return GenericError(
                error_code=FieldErrorCode.WRONG_TYPE,
                error_message='Field input must be a string',
                context={'field_name': field_name},
            )
        if input not in self.choices:
            return GenericError(
                error_code=FieldErrorCode.INVALID_CHOICE,
                error_message='Field input must be one of provided choices',
                context={'field_name': field_name},
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            'label': self.label,
            'is_requred': self.is_required,
            'choices': self.choices,
        }


class OpportunityForm(mongo.Document):
    id = mongo.IntField(primary_key=True)
    submit_method = mongo.EmbeddedDocumentField(SubmitMethod)
    fields = mongo.MapField(mongo.EmbeddedDocumentField(FormField))

    submit_method_factories: dict[str, Callable[[ser.OpportunityForm.SubmitMethod], SubmitMethod]] = {
        'noop': NoopSubmitMethod.create,
        'yandex_forms': YandexFormsSubmitMethod.create,
    }

    @classmethod
    def create_submit_method(cls, method: ser.OpportunityForm.SubmitMethod) -> SubmitMethod:
        """Method, that encapsulates creation methods of all submit methods."""

        factory = cls.submit_method_factories.get(method.type)
        if factory is None:
            raise ValueError(f'Unhandled submit method: {method.type}')
        return factory(method)

    field_factories: dict[str, Callable[[ser.OpportunityForm.Field], FormField]] = {
        'string': StringField.create,
        'regex': RegexField.create,
        'choice': ChoiceField.create,
    }

    @classmethod
    def create_field(cls, field: ser.OpportunityForm.Field) -> FormField:
        """Method, that encapsulates creatin methods of all form fields."""

        factory = cls.field_factories.get(field.type)
        if factory is None:
            raise ValueError(f'Unhandled field type: {field.type}')
        return factory(field)

    @classmethod
    def create_fields(cls, fields: ser.OpportunityForm.FormFields) -> dict[str, FormField]:
        return {name: cls.create_field(field) for name, field in fields.items()}

    @classmethod
    def create(cls, *, opportunity: '_opportunity.Opportunity', submit: ser.OpportunityForm.SubmitMethod | None = None,
               fields: ser.OpportunityForm.FormFields) -> Self:
        self = OpportunityForm(id=opportunity.id, fields=cls.create_fields(fields))
        if submit is None:
            self.submit_method = NoopSubmitMethod.create()
        else:
            self.submit_method = cls.create_submit(submit)
        self.save()
        return self

    def update_submit_method(self, submit: ser.OpportunityForm.SubmitMethod) -> None:
        self.submit_method = self.create_submit(submit)
        self.save()

    def update_fields(self, fields: ser.OpportunityForm.FormFields) -> None:
        self.fields = self.create_fields(fields)
        self.save()


class ResponseData(mongo.Document):
    id = mongo.IntField(primary_key=True)
    data = mongo.MapField(mongo.DynamicField())

    @classmethod
    def extra_field_error(field_name: str) -> FieldError:
        return GenericError(error_code=FieldErrorCode.EXTRA, error_message='Unexpected field',
                            context={'field_name': field_name})

    @classmethod
    def missing_field_error(field_name: str) -> FieldError:
        return GenericError(error_code=FieldErrorCode.MISSING, error_message='Missing required field',
                            context={'field_name': field_name})

    @classmethod
    def process_data(cls, form: OpportunityForm, data: ser.OpportunityResponse.Data,
                     validated_data: ser.OpportunityResponse.Data) -> Generator[FieldError]:
        for field_name, value in data.items():
            if not (field := form.fields.get(field_name)):
                yield cls.extra_field_error(field_name)
                continue
            if error := field.validate_input(field_name, value):
                yield error
                continue
            validated_data[field_name] = value
        for field_name, field in form.fields.items():
            if not field.is_required or field_name in data:
                continue
            yield cls.missing_field_error(field_name)

    @classmethod
    def create(cls, *, response: '_response.OpportunityResponse', form: OpportunityForm,
               data: ser.OpportunityResponse.Create) -> Self | list[FieldError]:
        validated_data: dict[str, Any] = {}
        if len(errors := list(cls.process_data(form, data, validated_data))) > 0:
            return errors
        self = ResponseData(id=response.id, data=validated_data)
        self.save()
        return self


from . import response as _response
