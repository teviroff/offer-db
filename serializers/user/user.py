from serializers.base import *
from pydantic import field_validator
from pydantic_core import PydanticCustomError
from ipaddress import IPv4Address
import re


class Credentials(BaseModel):
    """Model used for registration/login DB API methods."""

    model_config = {'extra': 'ignore'}

    email: Annotated[str, Field(max_length=50)]
    password: Annotated[str, Field(min_length=8)]

    @field_validator('email')
    @classmethod
    def email_regex(cls, email: str) -> str:
        regex = re.compile(r'^((?!\.)[\w\-_.]*[^.])(@\w+)(\.\w+(\.\w+)?[^.\W])$')
        if not regex.match(email):
            raise PydanticCustomError('pattern_error', 'Input should be a valid email address')
        return email

    @field_validator('password')
    @classmethod
    def password_regex(cls, password: str) -> str:
        regex = re.compile(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[.\-@$!%*?&])[A-Za-z\d.-@$!%*?&]*$')
        if not regex.match(password):
            raise PydanticCustomError('pattern_error', 'Input should be a valid password')
        return password


class Login(Credentials):
    """Model with information about login attempt. Used only by middleware."""

    ip: IPv4Address
    remember_me: Annotated[bool, Field(default=False)]
