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
import enum

import async_channel.channels as channel_instances
import octobot_commons.channels_name as channels_name
import octobot_commons.logging as logging
import octobot_commons.enums as enums
import octobot_commons.constants as commons_constants

import octobot_trading.errors as errors
import octobot_trading.exchanges as exchanges
import octobot_trading.util as util

OCTOBOT_CHANNEL_TRADING_CONSUMER_LOGGER_TAG = "OctoBotChannelTradingConsumer"


class OctoBotChannelTradingActions(enum.Enum):
    """
    OctoBot Channel consumer supported actions
    """

    EXCHANGE = "exchange"


class OctoBotChannelTradingDataKeys(enum.Enum):
    """
    OctoBot Channel consumer supported data keys
    """

    EXCHANGE_NAME = "exchange_name"
    EXCHANGE_CONFIG = "exchange_config"
    EXCHANGE_ID = "exchange_id"
    BACKTESTING = "backtesting"
    MATRIX_ID = "matrix_id"
    TENTACLES_SETUP_CONFIG = "tentacles_setup_config"
    AUTHENTICATOR = "authenticator"


async def octobot_channel_callback(bot_id, subject, action, data) -> None:
    """
    OctoBot channel consumer callback
    :param bot_id: the callback bot id
    :param subject: the callback subject
    :param action: the callback action
    :param data: the callback data
    """
    if subject == enums.OctoBotChannelSubjects.CREATION.value:
        await _handle_creation(bot_id, action, data)


async def _handle_creation(bot_id, action, data):
    if action == OctoBotChannelTradingActions.EXCHANGE.value:
        try:
            exchange_name = data.get(OctoBotChannelTradingDataKeys.EXCHANGE_NAME.value, None)
            config = data[OctoBotChannelTradingDataKeys.EXCHANGE_CONFIG.value]
            exchange_builder = exchanges.create_exchange_builder_instance(config, exchange_name) \
                .has_matrix(data[OctoBotChannelTradingDataKeys.MATRIX_ID.value]) \
                .use_tentacles_setup_config(data[OctoBotChannelTradingDataKeys.TENTACLES_SETUP_CONFIG.value]) \
                .use_community_authenticator(data.get(OctoBotChannelTradingDataKeys.AUTHENTICATOR.value, None)) \
                .set_bot_id(bot_id)
            set_exchange_type_details(exchange_builder, config, data[OctoBotChannelTradingDataKeys.BACKTESTING.value])
            await exchange_builder.build()
            await channel_instances.get_chan_at_id(channels_name.OctoBotChannelsName.OCTOBOT_CHANNEL.value,
                                                   bot_id).get_internal_producer() \
                .send(bot_id=bot_id,
                      subject=enums.OctoBotChannelSubjects.NOTIFICATION.value,
                      action=action,
                      data={OctoBotChannelTradingDataKeys.EXCHANGE_ID.value: exchange_builder.exchange_manager.id})
        except errors.TradingModeIncompatibility as e:
            logging.get_logger(OCTOBOT_CHANNEL_TRADING_CONSUMER_LOGGER_TAG).error(
                f"Error when initializing trading mode, {exchange_name} "
                f"exchange connection is closed to increase performances: {e}")
        except Exception as e:
            logging.get_logger(OCTOBOT_CHANNEL_TRADING_CONSUMER_LOGGER_TAG).exception(
                e,
                True,
                f"Error when creating a new {exchange_name} exchange connexion: {e.__class__.__name__} {e}")


def set_exchange_type_details(exchange_builder, config, backtesting):
    # real, simulator, backtesting
    if util.is_trader_enabled(config):
        exchange_builder.is_real()
    elif util.is_trader_simulator_enabled(config):
        exchange_builder.is_simulated()
    if backtesting is not None:
        exchange_builder.is_simulated()
        exchange_builder.is_rest_only()
        exchange_builder.is_backtesting(backtesting)
    # use exchange sandbox
    exchange_builder.is_sandboxed(
        config[commons_constants.CONFIG_EXCHANGES].get(exchange_builder.exchange_name, {}).get(
            commons_constants.CONFIG_EXCHANGE_SANDBOXED, False)
    )
    # exchange trading type
    if config[commons_constants.CONFIG_EXCHANGES].get(exchange_builder.exchange_name, {}).get(
            commons_constants.CONFIG_EXCHANGE_FUTURE, False):
        exchange_builder.is_future(True)
    elif config[commons_constants.CONFIG_EXCHANGES].get(exchange_builder.exchange_name, {}).get(
            commons_constants.CONFIG_EXCHANGE_MARGIN, False):
        exchange_builder.is_margin(True)
    elif config[commons_constants.CONFIG_EXCHANGES].get(exchange_builder.exchange_name, {}).get(
            commons_constants.CONFIG_EXCHANGE_SPOT, True):
        # Use spot trading as default trading type
        exchange_builder.is_spot_only(True)

    # rest, web socket
    if config[commons_constants.CONFIG_EXCHANGES].get(exchange_builder.exchange_name, {}).get(
            commons_constants.CONFIG_EXCHANGE_REST_ONLY, False):
        exchange_builder.is_rest_only()
