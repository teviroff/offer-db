from pydantic import HttpUrl, field_validator
from pydantic_core import PydanticCustomError

from ..base import *
from . import form


type Name = Annotated[str, Field(min_length=1, max_length=100)]

class Create(BaseModel):
    model_config = {'extra': 'ignore'}

    name: Name
    link: Annotated[HttpUrl | None, Field(default=None)]
    provider_id: Id

    @field_validator('link')
    @classmethod
    def validate_link_length(cls, link: HttpUrl) -> str:
        if len(str(link)) > 120:
            raise PydanticCustomError('string_too_long', 'Opportunity URL can contain at most 120 characters')
        return link


class Filter(BaseModel):
    model_config = {'extra': 'ignore'}

    provider_ids: Annotated[list[Id], Field(default_factory=list)]
    tag_ids: Annotated[list[Id], Field(default_factory=list)]
    geotag_ids: Annotated[list[Id], Field(default_factory=list)]
    page: Annotated[int, Field(default=1, ge=1)]


class AddTags(BaseModel):
    model_config = {'extra': 'ignore'}

    tag_ids: list[Id]


class AddGeoTags(BaseModel):
    model_config = {'extra': 'ignore'}

    geo_tag_ids: list[Id]


class UpdateFormSubmitMethod(BaseModel):
    model_config = {'extra': 'ignore'}

    submit_method: form.SubmitMethod


class UpdateFormFields(BaseModel):
    model_config = {'extra': 'ignore'}

    fields: form.Fields
