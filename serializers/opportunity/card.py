from ..base import *


type Title = Annotated[str, Field(min_length=1, max_length=30)]
type Subtitle = Annotated[str, Field(min_length=1, max_length=30)]

class Create(BaseModel):
    model_config = {'extra': 'ignore'}

    title: Title
    subtitle: Annotated[Subtitle | None, Field(default=None)]
