import typing as t
from collections.abc import Mapping, MutableMapping


class DictBaseMixin(Mapping):
    _mapping: t.Dict[str, t.Any] = {}

    def __getitem__(self, key: str) -> t.Any:
        return self._mapping[key]

    def __iter__(self) -> t.Iterator[str]:
        return iter(self._mapping)

    def __len__(self) -> int:
        return len(self._mapping)


class MutableDictMixin(DictBaseMixin, MutableMapping):
    def __setitem__(self, key: str, value: t.Any):
        self._mapping[key] = value

    def __delitem__(self, key: str):
        del self._mapping[key]

    def add(self, name: str, item: t.Any):
        self[name] = item


class Context(MutableDictMixin):
    @classmethod
    def init(cls, settings, **kwargs):
        raise NotImplementedError

    def start(self, **kwargs):
        pass

    def shutdown(self, **kwargs):
        pass

    def register(self, name: str, ctx: t.Any):
        self.add(name, ctx)

    @classmethod
    def get(cls, name: str | None = None) -> t.Any:
        if name is None:
            return cls._mapping
        try:
            return cls._mapping[name]
        except KeyError:
            raise KeyError(f"Context '{name}' not found")
