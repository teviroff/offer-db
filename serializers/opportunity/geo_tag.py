from ..base import *


class Create(BaseModel):
    model_config = {'extra': 'ignore'}

    city_id: Id
