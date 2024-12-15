from ..base import *
from .. import auxillary as _


type Name = Annotated[str, Field(max_length=50)]
type Surname = Annotated[str, Field(max_length=50)]

class Update(BaseModel):
    model_config = {'extra': 'ignore'}

    name: Name | None = None
    surname: Surname | None = None
    birthday: _.Date | None = None
    city_id: Id | None = None


class UpdatePhoneNumber(BaseModel):
    ...
