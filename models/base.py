from enum import Enum
from typing import BinaryIO
from dataclasses import dataclass

from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Session, Mapped, mapped_column, relationship

import logging

logger = logging.getLogger('database')


class Base(DeclarativeBase):
    pass


@dataclass
class FileStream[F: Enum]:
    stream: BinaryIO
    format: F
    size: int | None
