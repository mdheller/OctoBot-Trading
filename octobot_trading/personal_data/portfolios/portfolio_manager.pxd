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
cimport octobot_trading.personal_data as personal_data
cimport octobot_trading.exchanges as exchanges
cimport octobot_trading.util as util


cdef class PortfolioManager(util.Initializable):
    cdef object logger

    cdef public dict config

    cdef public str reference_market

    cdef public exchanges.ExchangeManager exchange_manager
    cdef public exchanges.Trader trader

    cdef public personal_data.PortfolioProfitability portfolio_profitability
    cdef public personal_data.PortfolioValueHolder portfolio_value_holder
    cdef public personal_data.Portfolio portfolio

    cpdef bint handle_balance_update(self, dict balance, bint is_diff_update=*)
    cpdef void clear(self)

    cdef void _load_portfolio(self)
    cdef void _set_starting_simulated_portfolio(self)
    cdef bint _refresh_simulated_trader_portfolio_from_order(self, object order)