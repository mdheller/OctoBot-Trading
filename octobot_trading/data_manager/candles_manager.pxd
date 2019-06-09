# cython: language_level=3
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
#  Lesser General License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.
from octobot_trading.util.initializable cimport Initializable

cimport numpy as np
np.import_array()

cdef class CandlesManager(Initializable):
    cdef object logger
    
    cdef np.float64_t[::1] close_candles
    cdef np.float64_t[::1] open_candles
    cdef np.float64_t[::1] high_candles
    cdef np.float64_t[::1] low_candles
    cdef np.float64_t[::1] time_candles
    cdef np.float64_t[::1] volume_candles

    cdef int close_candles_index
    cdef int open_candles_index
    cdef int high_candles_index
    cdef int low_candles_index
    cdef int time_candles_index
    cdef int volume_candles_index

    cpdef np.float64_t get_symbol_close_candles(self, object limit=*)
    cpdef np.float64_t get_symbol_open_candles(self, object limit=*)
    cpdef np.float64_t get_symbol_high_candles(self, object limit=*)
    cpdef np.float64_t get_symbol_low_candles(self, object limit=*)
    cpdef np.float64_t get_symbol_time_candles(self, object limit=*)
    cpdef np.float64_t get_symbol_volume_candles(self, object limit=*)
    cpdef dict get_symbol_prices(self, object limit=*)
    cpdef add_new_candle(self, dict new_candle_data)

    # private
    cdef _set_all_candles(self, object new_candles_data)
    cdef _change_current_candle(self)
    cdef _should_add_new_candle(self, new_open_time)
    cdef _inc_candle_index(self)

    @staticmethod
    cdef _extract_limited_data(np.float64_t[::1] data, object limit=*)