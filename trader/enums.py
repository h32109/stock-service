from enum import Enum


class StrEnum(str, Enum):
    ...


class Environment(StrEnum):
    PROD = "production"
    DEV = "development"
    TEST = "test"
