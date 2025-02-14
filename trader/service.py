import asyncio
import typing as t


class ServiceBase:
    def configuration(self, settings):
        raise NotImplementedError


class Service:
    __services: t.Dict[str, ServiceBase] = {}

    @classmethod
    def add_service(cls, service_class: t.Type[ServiceBase]) -> ServiceBase:
        service_name = service_class.__name__
        if service_name in cls.__services:
            return cls.__services[service_name]

        service = service_class()
        setattr(cls, service_name, service)
        cls.__services[service_name] = service
        return service

    @classmethod
    async def init(cls, settings):
        coroutines = []
        for svc in cls.__services.values():
            if hasattr(svc, 'configuration') and callable(getattr(svc, 'configuration')):
                coroutines.append(svc.configuration(settings))
        await asyncio.gather(*coroutines)

    @classmethod
    def get(cls, service_name: str) -> ServiceBase:
        try:
            return cls.__services[service_name]
        except KeyError:
            raise ValueError(f"Service '{service_name}' not found.")