import typing as t

from trader.stock.model import (
    Stock,
    StockPrice,
    LargeIndustry,
    MediumIndustry,
    SmallIndustry,
    StockPriceHistory
)

# from trader.order.model import (
#     Order,
#     OrderHistory,
#     Transaction
# )


def get_models() -> t.List[t.Any]:
    return [
        Stock,
        StockPrice,
        LargeIndustry,
        MediumIndustry,
        SmallIndustry,
        StockPriceHistory,
        # Order,
        # OrderHistory,
        # Transaction
    ]
