from enum import IntEnum

class GenericError[T: IntEnum, Context = None]:
    error_code: T
    error_message: str
    context: Context

    def __init__(self, error_code: T, error_message: str, context: Context = None) -> None:
        self.error_code = error_code
        self.error_message = error_message
        self.context = context
