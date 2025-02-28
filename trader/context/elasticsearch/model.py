from enum import Enum


class ElasticsearchIndex(Enum):
    TRADES = "trades_{market}"
    ORDERS = "orders_{market}"
    TICKERS = "tickers_{market}"

    @property
    def value(self) -> str:
        return self._value_