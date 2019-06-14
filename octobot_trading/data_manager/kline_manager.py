#  Drakkar-Software OctoBot-Trading
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.
from math import nan
from octobot_commons.enums import PriceIndexes
from octobot_commons.logging.logging_util import get_logger

from octobot_trading.util.initializable import Initializable


class KlineManager(Initializable):
    def __init__(self):  # TODO to be removed
        super().__init__()
        self.logger = get_logger(self.__class__.__name__)
        self.kline = {}

    async def initialize_impl(self, last_candle):
        self.reset_kline(last_candle)

    def _reset_kline(self):
        self.kline = {
            PriceIndexes.IND_PRICE_CLOSE.value: nan,
            PriceIndexes.IND_PRICE_OPEN.value: nan,
            PriceIndexes.IND_PRICE_HIGH.value: nan,
            PriceIndexes.IND_PRICE_LOW.value: nan,
            PriceIndexes.IND_PRICE_VOL.value: nan,
            PriceIndexes.IND_PRICE_TIME.value: nan
        }

    def reset_kline(self, last_candle):
        self._reset_kline()
        if last_candle:
            self.kline[PriceIndexes.IND_PRICE_TIME.value] = last_candle[PriceIndexes.IND_PRICE_TIME.value]
            self.kline[PriceIndexes.IND_PRICE_OPEN.value] = last_candle[PriceIndexes.IND_PRICE_CLOSE.value]

    def kline_update(self, kline):
        if kline:
            if self.kline[PriceIndexes.IND_PRICE_VOL.value] is nan:
                self.kline[PriceIndexes.IND_PRICE_VOL.value] = kline[PriceIndexes.IND_PRICE_VOL.value]
            else:
                self.kline[PriceIndexes.IND_PRICE_VOL.value] += kline[PriceIndexes.IND_PRICE_VOL.value]

            self.kline[PriceIndexes.IND_PRICE_CLOSE.value] = kline[PriceIndexes.IND_PRICE_CLOSE.value]

            if self.kline[PriceIndexes.IND_PRICE_HIGH.value] is nan or \
                    self.kline[PriceIndexes.IND_PRICE_HIGH.value] < kline[PriceIndexes.IND_PRICE_HIGH.value]:
                self.kline[PriceIndexes.IND_PRICE_HIGH.value] = kline[PriceIndexes.IND_PRICE_HIGH.value]

            if self.kline[PriceIndexes.IND_PRICE_LOW.value] is nan or \
                    self.kline[PriceIndexes.IND_PRICE_LOW.value] > kline[PriceIndexes.IND_PRICE_LOW.value]:
                self.kline[PriceIndexes.IND_PRICE_LOW.value] = kline[PriceIndexes.IND_PRICE_LOW.value]