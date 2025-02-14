import typing as t

from trader.stock.model import (
    Stock,
    StockPrice,
    Industry,
    StockPriceHistory
)


def get_models() -> t.List[t.Any]:
    return [
        Stock,
        StockPrice,
        Industry,
        StockPriceHistory
    ]
