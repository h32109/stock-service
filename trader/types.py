from enum import Enum
import typing as t


class StrEnum(str, Enum):
    ...


ObjectType = t.Dict[str, t.Any]
