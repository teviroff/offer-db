from typing import Annotated, TypeIs

from pydantic import BaseModel, Field

API_KEY_PATTERN: str = r'^(dev|personal)\-[0-9a-f]{64}$'

type APIKey = Annotated[str, Field(pattern=API_KEY_PATTERN)]
type Id = Annotated[int, Field(ge=1)]


def assert_api_key(key: str) -> TypeIs[APIKey]:
    import re

    return re.match(API_KEY_PATTERN, key)

class APIKeyModel(BaseModel):
    model_config = {'extra': 'ignore'}

    api_key: APIKey
