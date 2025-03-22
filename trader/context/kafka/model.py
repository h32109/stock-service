import pydantic as pyd
import typing as t

from trader import types


class Data(pyd.BaseModel):
    messages: t.Union[
        t.Optional[types.ObjectType], t.List[types.ObjectType], t.List[str], t.Dict
    ]

    async def chunk(self, chunk_size: int):
        """
        If data size is too big, data should be chunked as proper size.

        Args:
            chunk_size:
        Returns:
             Data model
        """
        if chunk_size > 0:
            contents = [
                self.contents[i:i + chunk_size]
                for i in range(0, len(self.contents), chunk_size)
            ]
            _meta = self.dict()
            _meta.pop("contents")
            for chunked_content in contents:
                yield self.__class__(
                    **_meta,
                    contents=chunked_content
                )
        else:
            yield self