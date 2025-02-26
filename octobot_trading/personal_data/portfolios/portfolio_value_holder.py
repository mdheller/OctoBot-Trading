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
import asyncio

import octobot_commons.constants as common_constants
import octobot_commons.logging as logging
import octobot_commons.symbol_util as symbol_util

import octobot_trading.constants as constants


class PortfolioValueHolder:
    """
    PortfolioValueHolder calculates the current and the origin portfolio value in reference market for each updates
    """

    def __init__(self, portfolio_manager):
        self.portfolio_manager = portfolio_manager
        self.logger = logging.get_logger(f"{self.__class__.__name__}"
                                         f"[{self.portfolio_manager.exchange_manager.exchange_name}]")

        self.initializing_symbol_prices = set()

        self.portfolio_origin_value = constants.ZERO
        self.portfolio_current_value = constants.ZERO

        # values in decimal.Decimal
        self.last_prices_by_trading_pair = {}
        self.origin_portfolio = None

        # values in decimal.Decimal
        self.origin_crypto_currencies_values = {}
        self.current_crypto_currencies_values = {}

        # set of currencies for which the current exchange is not providing any suitable price data
        self.missing_currency_data_in_exchange = set()

    def update_origin_crypto_currencies_values(self, symbol, mark_price):
        """
        Update origin cryptocurrencies value
        :param symbol: the symbol to update
        :param mark_price: the symbol mark price value in decimal.Decimal
        :return: True if the origin portfolio should be recomputed
        """
        currency, market = symbol_util.split_symbol(symbol)
        # update origin values if this price has relevant data regarding the origin portfolio (using both quote and base)
        origin_currencies_should_be_updated = (
            (
                currency not in set(self.origin_crypto_currencies_values.keys()) and
                market == self.portfolio_manager.reference_market
            )
            or
            (
                market not in set(self.origin_crypto_currencies_values.keys()) and
                currency == self.portfolio_manager.reference_market
            )
        )
        if origin_currencies_should_be_updated:
            # will fail if symbol doesn't have a price in self.origin_crypto_currencies_values and therefore
            # requires the origin portfolio value to be recomputed using this price info in case this price is relevant
            if market == self.portfolio_manager.reference_market:
                self.origin_crypto_currencies_values[currency] = mark_price
            else:
                self.origin_crypto_currencies_values[market] = constants.ONE / mark_price
        self.last_prices_by_trading_pair[symbol] = mark_price
        return origin_currencies_should_be_updated

    def get_current_crypto_currencies_values(self):
        """
        Return the current crypto-currencies values
        :return: the current crypto-currencies values
        """
        if not self.current_crypto_currencies_values:
            self._update_portfolio_and_currencies_current_value()
        return self.current_crypto_currencies_values

    def get_current_holdings_values(self):
        """
        Get holdings ratio for each currencies
        :return: the holdings ratio dictionary
        """
        holdings = self.get_current_crypto_currencies_values()
        return {currency: self._get_currency_value(self.portfolio_manager.portfolio.portfolio, currency, holdings)
                for currency in holdings.keys()}

    def get_currency_holding_ratio(self, currency):
        """
        Return the holdings ratio for the specified currency
        :param currency: the currency
        :return: the holdings ratio
        """
        return self._evaluate_value(currency, self.portfolio_manager.portfolio.get_currency_from_given_portfolio(
            currency, common_constants.PORTFOLIO_TOTAL)) / self.portfolio_current_value \
            if self.portfolio_current_value else constants.ZERO

    async def handle_profitability_recalculation(self, force_recompute_origin_portfolio) -> None:
        """
        Initialize values required by portfolio profitability to perform its profitability calculation
        :param force_recompute_origin_portfolio: when True, force origin portfolio computation
        """
        self._update_portfolio_and_currencies_current_value()
        await self._init_portfolio_values_if_necessary(force_recompute_origin_portfolio)

    def get_origin_portfolio_current_value(self, refresh_values=False):
        """
        Calculates and return the origin portfolio actual value
        :param refresh_values: when True, force origin portfolio reevaluation
        :return: the origin portfolio current value
        """
        if refresh_values:
            self.current_crypto_currencies_values.update(
                self._evaluate_config_crypto_currencies_and_portfolio_values(self.origin_portfolio.portfolio))
        return self._update_portfolio_current_value(self.origin_portfolio.portfolio,
                                                    currencies_values=self.current_crypto_currencies_values)

    async def _init_portfolio_values_if_necessary(self, force_recompute_origin_portfolio) -> None:
        """
        Init origin portfolio values if necessary
        :param force_recompute_origin_portfolio: when True, force origin portfolio computation
        """
        if self.portfolio_origin_value == constants.ZERO:
            # try to update portfolio origin value if it's not known yet
            await self._init_origin_portfolio_and_currencies_value()
        if force_recompute_origin_portfolio:
            self._recompute_origin_portfolio_initial_value()

    async def _init_origin_portfolio_and_currencies_value(self) -> None:
        """
        Initialize origin portfolio and the origin portfolio currencies values
        """
        self.origin_portfolio = self.origin_portfolio or await self.portfolio_manager.portfolio.copy()
        self.origin_crypto_currencies_values.update(
            self._evaluate_config_crypto_currencies_and_portfolio_values(self.origin_portfolio.portfolio,
                                                                         ignore_missing_currency_data=True))
        self._recompute_origin_portfolio_initial_value()

    def _update_portfolio_current_value(self, portfolio, currencies_values=None, fill_currencies_values=False):
        """
        Update the portfolio with current prices
        :param portfolio: the portfolio to update
        :param currencies_values: the currencies values
        :param fill_currencies_values: the currencies values to calculate
        :return: the updated portfolio
        """
        values = currencies_values
        if values is None or fill_currencies_values:
            self.current_crypto_currencies_values.update(
                self._evaluate_config_crypto_currencies_and_portfolio_values(portfolio))
            if fill_currencies_values:
                self._fill_currencies_values(currencies_values)
            values = self.current_crypto_currencies_values
        return self._evaluate_portfolio_value(portfolio, values)

    def _fill_currencies_values(self, currencies_values):
        """
        Fill a currency values dict with new data
        :param currencies_values: currencies values dict to be filled
        """
        currencies_values.update({
            currency: value
            for currency, value in self.current_crypto_currencies_values.items()
            if currency not in currencies_values
        })

    def _update_portfolio_and_currencies_current_value(self):
        """
        Update the portfolio current value with the current portfolio instance
        """
        self.portfolio_current_value = self._update_portfolio_current_value(
            self.portfolio_manager.portfolio.portfolio)

    def _evaluate_value(self, currency, quantity, raise_error=True):
        """
        Evaluate value returns the currency quantity value in the reference (attribute) currency
        :param currency: the currency to evaluate
        :param quantity: the currency quantity
        :param raise_error: will catch exception if False
        :return: the currency value
        """
        # easy case --> the current currency is the reference currency or the quantity is 0
        if currency == self.portfolio_manager.reference_market or quantity == constants.ZERO:
            return quantity
        currency_value = self._try_get_value_of_currency(currency, quantity, raise_error)
        return self._check_currency_initialization(currency=currency, currency_value=currency_value)

    def _check_currency_initialization(self, currency, currency_value):
        """
        Check if the currency has to be removed from self.initializing_symbol_prices and return currency_value
        :param currency: the currency to check
        :param currency_value: the currency value
        :return: currency_value after checking
        """
        if currency_value > constants.ZERO and currency in self.initializing_symbol_prices:
            self.initializing_symbol_prices.remove(currency)
        return currency_value

    def _recompute_origin_portfolio_initial_value(self):
        """
        Compute origin portfolio initial value and update portfolio_origin_value
        """
        self.portfolio_origin_value = \
            self._update_portfolio_current_value(self.origin_portfolio.portfolio,
                                                 currencies_values=self.origin_crypto_currencies_values,
                                                 fill_currencies_values=True)

    def _try_get_value_of_currency(self, currency, quantity, raise_error):
        """
        try_get_value_of_currency will try to obtain the current value of the currency quantity in reference currency.
        It will try to create the symbol that fit with the exchange logic.
        :return: the value found of this currency quantity, if not found returns 0.
        """
        symbol = symbol_util.merge_currencies(currency, self.portfolio_manager.reference_market)
        reversed_symbol = symbol_util.merge_currencies(self.portfolio_manager.reference_market, currency)

        try:
            if self.portfolio_manager.exchange_manager.symbol_exists(symbol):
                return self.last_prices_by_trading_pair[symbol] * quantity

            if self.portfolio_manager.exchange_manager.symbol_exists(reversed_symbol) and \
                    self.last_prices_by_trading_pair[reversed_symbol] != constants.ZERO:
                return quantity / self.last_prices_by_trading_pair[reversed_symbol]

            if currency not in self.missing_currency_data_in_exchange:
                self._inform_no_matching_symbol(currency)
                self.missing_currency_data_in_exchange.add(currency)
        except KeyError as missing_data_exception:
            if not self.portfolio_manager.exchange_manager.is_backtesting:
                self._try_to_ask_ticker_missing_symbol_data(currency, symbol, reversed_symbol)
                if raise_error:
                    raise missing_data_exception
        return constants.ZERO

    def _try_to_ask_ticker_missing_symbol_data(self, currency, symbol, reversed_symbol):
        """
        Try to ask the ticker producer to watch additional symbols
        to collect missing data required for profitability calculation
        :param currency: the concerned currency
        :param symbol: the symbol to add
        :param reversed_symbol: the reversed symbol to add
        """
        symbols_to_add = []
        if self.portfolio_manager.exchange_manager.symbol_exists(symbol):
            symbols_to_add = [symbol]
        elif self.portfolio_manager.exchange_manager.symbol_exists(reversed_symbol):
            symbols_to_add = [reversed_symbol]

        if symbols_to_add:
            self._ask_ticker_data_for_currency(symbols_to_add)
            self.initializing_symbol_prices.add(currency)

    def _ask_ticker_data_for_currency(self, symbols_to_add):
        """
        Synchronously call TICKER_CHANNEL producer to add a list of new symbols to its watch list
        :param symbols_to_add: the list of symbol to add to the TICKER_CHANNEL producer watch list
        """
        asyncio.run_coroutine_threadsafe(
            self.portfolio_manager.exchange_manager.exchange_config.add_watched_symbols(symbols_to_add),
            asyncio.get_running_loop())

    def _inform_no_matching_symbol(self, currency):
        """
        Log a missing currency pair to calculate the portfolio profitability
        :param currency: the concerned currency
        """
        # do not log warning in backtesting or tests
        if not self.portfolio_manager.exchange_manager.is_backtesting:
            self.logger.warning(f"No trading pair including {currency} and {self.portfolio_manager.reference_market} on"
                                f" {self.portfolio_manager.exchange_manager.exchange_name}. {currency} "
                                f"can't be valued for portfolio and profitability.")

    def _evaluate_config_crypto_currencies_and_portfolio_values(self,
                                                                portfolio,
                                                                ignore_missing_currency_data=False):
        """
        Evaluate both config and portfolio currencies values
        :param portfolio: the current portfolio
        :param ignore_missing_currency_data: when True, ignore missing currencies values in calculation
        :return: the result of config and portfolio currencies values calculation
        """
        evaluated_pair_values = {}
        evaluated_currencies = set()
        missing_tickers = set()

        self._evaluate_config_currencies_values(evaluated_pair_values, evaluated_currencies, missing_tickers)
        self._evaluate_portfolio_currencies_values(portfolio, evaluated_pair_values, evaluated_currencies,
                                                   missing_tickers, ignore_missing_currency_data)

        if missing_tickers:
            self.logger.debug(f"Missing price data for {missing_tickers}, impossible to compute all the "
                              f"currencies values for now.")
        return evaluated_pair_values

    def _evaluate_config_currencies_values(self, evaluated_pair_values, evaluated_currencies, missing_tickers):
        """
        Evaluate config currencies values
        TODO do not use config[CONFIG_CRYPTO_CURRENCIES]
        :param evaluated_pair_values: the list of evaluated pairs
        :param evaluated_currencies: the list of evaluated currencies
        :param missing_tickers: the list of missing currencies
        """
        if self.portfolio_manager.exchange_manager.exchange_config.all_config_symbol_pairs:
            currency, market = symbol_util.split_symbol(
                self.portfolio_manager.exchange_manager.exchange_config.all_config_symbol_pairs[0]
            )
            currency_to_evaluate = currency
            try:
                if currency not in evaluated_currencies:
                    evaluated_pair_values[currency] = self._evaluate_value(currency, constants.ONE)
                    evaluated_currencies.add(currency)
                if market not in evaluated_currencies:
                    currency_to_evaluate = market
                    evaluated_pair_values[market] = self._evaluate_value(market, constants.ONE)
                    evaluated_currencies.add(market)
            except KeyError:
                missing_tickers.add(currency_to_evaluate)

    def _evaluate_portfolio_currencies_values(self,
                                              portfolio,
                                              evaluated_pair_values,
                                              evaluated_currencies,
                                              missing_tickers,
                                              ignore_missing_currency_data):
        """
        Evaluate current portfolio currencies values
        :param portfolio: the current portfolio
        :param evaluated_pair_values: the list of evaluated pairs
        :param evaluated_currencies: the list of evaluated currencies
        :param missing_tickers: the list of missing currencies
        :param ignore_missing_currency_data: when True, ignore missing currencies values in calculation
        """
        for currency in portfolio:
            try:
                if currency not in evaluated_currencies and self._should_currency_be_considered(
                        currency, portfolio, ignore_missing_currency_data):
                    evaluated_pair_values[currency] = self._evaluate_value(currency, constants.ONE)
                    evaluated_currencies.add(currency)
            except KeyError:
                missing_tickers.add(currency)

    def _evaluate_portfolio_value(self, portfolio, currencies_values=None):
        """
        Perform evaluate_value with a portfolio configuration
        :param portfolio: the portfolio to explore
        :param currencies_values: currencies to evaluate
        :return: the calculated quantity value in reference (attribute) currency
        """
        return sum([
            self._get_currency_value(portfolio, currency, currencies_values)
            for currency in portfolio
            if currency not in self.missing_currency_data_in_exchange
        ])

    def _get_currency_value(self, portfolio, currency, currencies_values=None, raise_error=False):
        """
        Return the currency value
        :param portfolio: the specified portfolio
        :param currency: the currency to evaluate
        :param currencies_values: currencies values dict
        :param raise_error: When True, forward exceptions
        :return: the currency value
        """
        if currency in portfolio and portfolio[currency][constants.CONFIG_PORTFOLIO_TOTAL] != constants.ZERO:
            if currencies_values and currency in currencies_values:
                return currencies_values[currency] * portfolio[currency][constants.CONFIG_PORTFOLIO_TOTAL]
            return self._evaluate_value(currency, portfolio[currency][constants.CONFIG_PORTFOLIO_TOTAL], raise_error)
        return constants.ZERO

    def _should_currency_be_considered(self, currency, portfolio, ignore_missing_currency_data):
        """
        Return True if enough data is available to evaluate currency value
        :param currency: the currency to evaluate
        :param portfolio: the specified portfolio
        :param ignore_missing_currency_data: When True, ignore check of currency presence
        in missing_currency_data_in_exchange
        :return: True if enough data is available to evaluate currency value
        """
        return (currency not in self.missing_currency_data_in_exchange or ignore_missing_currency_data) and \
               (portfolio[currency][common_constants.PORTFOLIO_TOTAL] > constants.ZERO or currency in
                self.portfolio_manager.portfolio_profitability.valuated_currencies)
