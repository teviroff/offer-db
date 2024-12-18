from typing import Any

from ..base import *


type Data = dict[str, Any]

class Create(BaseModel):
    model_config = {'extra': 'ignore'}

    data: Data
