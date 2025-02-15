import enum


class RedisKey(str, enum.Enum):
    API_KEY = "api_key:{api_key}"