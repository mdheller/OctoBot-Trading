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
cimport octobot_trading.personal_data.portfolios.portfolio as portfolio_class

cdef class MarginPortfolio(portfolio_class.Portfolio):
    cdef void _reset_currency_portfolio(self, str currency)
    cdef dict _parse_currency_balance(self, dict currency_balance)
    cdef dict _create_currency_portfolio(self, object available, object total, object margin=*)
    cdef void _set_currency_portfolio(self, str currency, object available, object total, object margin=*)

    # return object to ensure PortfolioNegativeValueError forwarding
    cdef object _update_currency_portfolio(self, str currency, object available=*, object total=*, object margin=*)
