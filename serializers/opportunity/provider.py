from serializers.base import *


type Name = Annotated[str, Field(min_length=4, max_length=50)]

class Create(BaseModel):
    model_config = {'extra': 'ignore'}

    name: Name

class UpdateLogo(BaseModel):
    ...
