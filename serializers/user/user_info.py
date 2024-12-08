from ..base import *
from .. import auxillary as _


type Name = Annotated[str, Field(max_length=50)]
type Surname = Annotated[str, Field(max_length=50)]

class Update(BaseModel):
    model_config = {'extra': 'ignore'}

    name: Annotated[Name | None, Field(default=None)]
    surname: Annotated[Surname | None, Field(default=None)]
    birthday: Annotated[_.Date | None, Field(default=None)]
    city_id: Annotated[Id | None, Field(default=None)]


class UpdatePhoneNumber(BaseModel):
    ...
