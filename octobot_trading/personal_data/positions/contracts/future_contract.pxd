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


cdef class FutureContract:
    cdef str pair

    cdef public object contract_type
    cdef public object margin_type

    cdef public double expiration_timestamp

    cdef public double minimum_tick_size
    cdef public object contract_size
    cdef public object current_leverage
    cdef public object maximum_leverage

    cpdef bint is_inverse_contract(self)
    cpdef bint is_isolated(self)
