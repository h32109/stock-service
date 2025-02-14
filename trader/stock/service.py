import typing as t

from trader.service import ServiceBase, Service


class StockServiceBase(ServiceBase):
    settings: t.Any

    async def configuration(self, settings):
        self.settings = settings


class StockService(StockServiceBase):
    pass

stock_service = Service.add_service(StockService)
