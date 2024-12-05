from typing import Any

from serializers.base import *


type Data = dict[str, Any]

class Create(BaseModel):
    model_config = {'extra': 'ignore'}

    data: Data
