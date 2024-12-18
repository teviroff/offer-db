from ..base import *


type Title = Annotated[str, Field(min_length=1, max_length=100)]
type Subtitle = Annotated[str, Field(min_length=1, max_length=50)]

class Create(BaseModel):
    model_config = {'extra': 'ignore'}

    title: Title
    subtitle: Annotated[Subtitle | None, Field(default=None)]
