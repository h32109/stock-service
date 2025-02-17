import random

import factory

from factory import fuzzy

from trader.stock.model import Stock

BaseMeta = factory.base.BaseMeta
Factory = factory.base.Factory
OptionDefault = factory.base.OptionDefault


class SQLFactory(Factory):
    """Factory for SQL dummy data"""

    class Meta:
        abstract = True

    @classmethod
    def create(cls, **kwargs):
        # 데이터 넣는 코드
        return


class FuzzyChoices(fuzzy.FuzzyChoice):

    def __init__(self, choices, k=1, getter=None):
        super().__init__(choices, getter)
        self.k = k

    def fuzz(self):
        if self.choices is None:
            self.choices = list(self.choices_generator)
        value = random.choices(self.choices, k=self.k)
        if self.getter is None:
            return value
        return self.getter(value)


class StockFactory(SQLFactory):
    class Meta:
        model = Stock

    pass