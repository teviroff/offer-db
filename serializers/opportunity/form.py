from typing import Literal
import re

from pydantic import field_validator, HttpUrl
from pydantic_core import PydanticCustomError

from ..base import Annotated, BaseModel, Field as _Field


class SubmitMethodBase(BaseModel):
    model_config = {'extra': 'ignore'}


class NoopSubmitMethod(SubmitMethodBase):
    type: Literal['noop']


class YandexFormsSubmitMethod(SubmitMethodBase):
    type: Literal['yandex_forms']
    url: HttpUrl

    @field_validator('url', mode='after')
    @classmethod
    def validate_host(cls, url: HttpUrl) -> HttpUrl:
        if url.host not in ['forms.yandex.ru']:
            raise PydanticCustomError('invalid_host', 'Invalid URL host')
        return url


class FieldBase(BaseModel):
    model_config = {'extra': 'ignore'}

    label: str
    is_required: Annotated[bool, _Field(strict=True)]


class StringField(FieldBase):
    type: Literal['string']
    max_length: Annotated[Annotated[int, _Field(ge=1)] | None, _Field(default=None)]


class RegexField(StringField):
    type: Literal['regex']
    regex: str

    @field_validator('regex')
    @classmethod
    def validate_regex(cls, regex: str) -> str:
        try:
            re.compile(regex)
        except re.PatternError:
            raise PydanticCustomError('pattern_error', 'Input should be a valid regular expression')
        return regex


class ChoiceField(FieldBase):
    type: Literal['choice']
    choices: Annotated[list[str], _Field(min_length=1)]


type SubmitMethod = Annotated[NoopSubmitMethod | YandexFormsSubmitMethod, _Field(discriminator='type')]
type Field = Annotated[StringField | RegexField | ChoiceField, _Field(discriminator='type')]
type Fields = Annotated[dict[str, Field], _Field(min_length=1)]
