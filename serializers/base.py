from typing import Annotated
from pydantic import BaseModel, Field

type APIKey = Annotated[str, Field(min_length=64, max_length=80, pattern=r'^(dev|personal)\-[0-9a-f]{64}$')]
type Id = Annotated[int, Field(ge=1)]
