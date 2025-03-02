import typing as t

from trader.stock.model import (
    Stock,
    StockPrice,
    LargeIndustry,
    MediumIndustry,
    SmallIndustry,
    StockPriceHistory
)


def get_models() -> t.List[t.Any]:
    return [
        Stock,
        StockPrice,
        LargeIndustry,
        MediumIndustry,
        SmallIndustry,
        StockPriceHistory
    ]
