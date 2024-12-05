from serializers.base import *


type Name = Annotated[str, Field(min_length=1, max_length=50)]

class Rename(BaseModel):
    model_config = {'extra': 'ignore'}

    name: Name
