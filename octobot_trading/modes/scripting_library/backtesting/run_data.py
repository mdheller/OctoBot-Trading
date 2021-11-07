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
import copy

import octobot_trading.enums as trading_enums
import octobot_commons.symbol_util as symbol_util
import octobot_commons.constants


async def get_candles(reader, pair):
    return await reader.select(trading_enums.DBTables.CANDLES.value, ((await reader.search()).pair == pair))


async def get_trades(reader, pair):
    return await reader.select(trading_enums.DBTables.ORDERS.value, (await reader.search()).pair == pair)


async def get_metadata(reader):
    return (await reader.all(trading_enums.DBTables.METADATA.value))[0]


async def get_starting_portfolio(reader) -> dict:
    return (await reader.all(trading_enums.DBTables.PORTFOLIO.value))[0]


async def _load_historical_values(reader, with_candles=True, with_trades=True, with_portfolio=True):
    price_data = {}
    trades_data = {}
    moving_portfolio_data = {}
    try:
        starting_portfolio = await get_starting_portfolio(reader)
        metadata = await get_metadata(reader)
        ref_market = metadata[trading_enums.DBRows.REFERENCE_MARKET.value]
        # init data
        for symbol, values in starting_portfolio.items():
            if symbol != ref_market:
                pair = symbol_util.merge_currencies(symbol, ref_market)
                if with_candles and pair not in price_data:
                    price_data[pair] = await get_candles(reader, pair)
                if with_trades and pair not in trades_data:
                    trades_data[pair] = await get_trades(reader, pair)
            if with_portfolio:
                moving_portfolio_data[symbol] = values[octobot_commons.constants.PORTFOLIO_TOTAL]
    except IndexError:
        pass
    return price_data, trades_data, moving_portfolio_data


async def plot_historical_portfolio_value(reader, plotted_element, own_yaxis=False):
    price_data, trades_data, moving_portfolio_data = await _load_historical_values(reader)
    time_data = []
    value_data = []
    for pair, candles in price_data.items():
        symbol, ref_market = symbol_util.split_symbol(pair)
        if candles and not time_data:
            time_data = [candle[trading_enums.PlotAttributes.X.value] for candle in candles]
            value_data = [0] * len(candles)
        for index, candle in enumerate(candles):
            # TODO: handle multiple pairs with shared symbols
            value_data[index] = \
                value_data[index] + \
                moving_portfolio_data[symbol] * candle[trading_enums.PlotAttributes.CLOSE.value] + moving_portfolio_data[ref_market]
            for trade in trades_data[pair]:
                if trade[trading_enums.PlotAttributes.X.value] == candle[trading_enums.PlotAttributes.X.value]:
                    if trade[trading_enums.PlotAttributes.SIDE.value] == "sell":
                        moving_portfolio_data[symbol] -= trade[trading_enums.PlotAttributes.VOLUME.value]
                        moving_portfolio_data[ref_market] += trade[trading_enums.PlotAttributes.VOLUME.value] * \
                                                             trade[trading_enums.PlotAttributes.Y.value]
                    else:
                        moving_portfolio_data[symbol] += trade[trading_enums.PlotAttributes.VOLUME.value]
                        moving_portfolio_data[ref_market] -= trade[trading_enums.PlotAttributes.VOLUME.value] * \
                                                             trade[trading_enums.PlotAttributes.Y.value]
                    if moving_portfolio_data[symbol] < 0 or moving_portfolio_data[ref_market] < 0:
                        raise RuntimeError("negative portfolio")

    plotted_element.plot(
        kind="scatter",
        x=time_data,
        y=value_data,
        title="Portfolio value",
        own_yaxis=own_yaxis)


async def plot_historical_pnl_value(reader, plotted_element, x_as_trade_count=True, own_yaxis=False):
    # PNL:
    # 1. open position: consider position opening fee from PNL
    # 2. close position: consider closed amount + closing fee into PNL
    # what is a trade ?
    #   futures: when position going to 0 (from long/short) => trade is closed
    #   spot: when position lowered => trade is closed
    price_data, trades_data, moving_portfolio_data = await _load_historical_values(reader)
    if not price_data:
        return
    x_data = [0 if x_as_trade_count else next(iter(price_data.values()))[0][trading_enums.PlotAttributes.X.value]]
    pnl_data = [0]
    for pair, candles in price_data.items():
        symbol, ref_market = symbol_util.split_symbol(pair)
        buy_order_volume_by_price = {}
        long_position_size = 0
        for trade in sorted(trades_data[pair], key=lambda x: x[trading_enums.PlotAttributes.X.value]):
            if trade[trading_enums.DBTables.PAIR.value] == pair:
                trade_volume = trade[trading_enums.PlotAttributes.VOLUME.value]
                if trade[trading_enums.PlotAttributes.SIDE.value] == trading_enums.TradeOrderSide.BUY.value:
                    if trade[trading_enums.PlotAttributes.Y.value] in buy_order_volume_by_price:
                        buy_order_volume_by_price[trade[trading_enums.PlotAttributes.Y.value]] += trade_volume
                    else:
                        buy_order_volume_by_price[trade[trading_enums.PlotAttributes.Y.value]] = trade_volume
                    # increase position size
                    long_position_size += trade_volume * trade[trading_enums.PlotAttributes.Y.value]
                elif trade[trading_enums.PlotAttributes.SIDE.value] == trading_enums.TradeOrderSide.SELL.value:
                    remaining_sell_volume = trade_volume
                    volume_by_bought_prices = {}
                    for order_price in sorted(buy_order_volume_by_price.keys()):
                        if buy_order_volume_by_price[order_price] > remaining_sell_volume:
                            buy_order_volume_by_price[order_price] -= remaining_sell_volume
                            volume_by_bought_prices[order_price] = remaining_sell_volume
                            remaining_sell_volume = 0
                        elif buy_order_volume_by_price[order_price] == remaining_sell_volume:
                            buy_order_volume_by_price.pop(order_price)
                            volume_by_bought_prices[order_price] = remaining_sell_volume
                            remaining_sell_volume = 0
                        else:
                            # buy_order_volume_by_price[order_price] < remaining_sell_volume
                            buy_volume = buy_order_volume_by_price.pop(order_price)
                            volume_by_bought_prices[order_price] = buy_volume
                            remaining_sell_volume -= buy_volume
                        if remaining_sell_volume <= 0:
                            break
                    if volume_by_bought_prices:
                        # use total_bought_volume only to avoid taking pre-existing open positions into account
                        # (ex if started with already 10 btc)
                        total_bought_volume = sum(volume for volume in volume_by_bought_prices.values())
                        average_buy_price = sum(price * (volume/total_bought_volume)
                                                for price, volume in volume_by_bought_prices.items())
                        fees = trade[trading_enums.DBTables.FEES_AMOUNT.value]
                        fees_multiplier = 1 if trade[trading_enums.DBTables.FEES_CURRENCY.value] == ref_market \
                            else trade[trading_enums.PlotAttributes.Y.value]
                        pnl = (trade[trading_enums.PlotAttributes.Y.value] - average_buy_price) * total_bought_volume - \
                              fees * fees_multiplier
                        pnl_data.append(pnl)
                        if x_as_trade_count:
                            x_data.append(len(pnl_data) - 1)
                        else:
                            x_data.append(trade[trading_enums.PlotAttributes.X.value])
            else:
                raise RuntimeError(f"Unknown trade side: {trade}")

    plotted_element.plot(
        kind="scatter",
        x=x_data,
        y=pnl_data,
        x_type="tick0" if x_as_trade_count else "date",
        title="P&L",
        own_yaxis=own_yaxis)

