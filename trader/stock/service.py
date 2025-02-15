import typing as t

from trader.service import ServiceBase, Service


class StockServiceBase(ServiceBase):
    config: t.Any

    async def configuration(self, config):
        self.config = config


class StockService(StockServiceBase):
    pass


stock_service = Service.add_service(StockService)
