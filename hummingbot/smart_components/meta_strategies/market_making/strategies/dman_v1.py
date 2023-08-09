import time
from decimal import Decimal

import pandas_ta as ta  # noqa: F401

from hummingbot.smart_components.executors.position_executor.data_types import PositionConfig, TrailingStop
from hummingbot.smart_components.executors.position_executor.position_executor import PositionExecutor
from hummingbot.smart_components.meta_strategies.data_types import MetaStrategyMode, OrderLevel
from hummingbot.smart_components.meta_strategies.market_making.market_making_strategy_base import (
    MarketMakingStrategyBase,
    MarketMakingStrategyConfigBase,
)


class DManConfig(MarketMakingStrategyConfigBase):
    strategy_name: str = "dman_v1"
    bbands_length: int = 20
    bbands_std: int = 2.0
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    natr_length: int = 14


class DMan(MarketMakingStrategyBase):
    """
    Directional Market Making Strategy
    """
    def __init__(self, config: DManConfig, mode: MetaStrategyMode = MetaStrategyMode.LIVE):
        super().__init__(config, mode)
        self.config = config

    def early_stop_condition(self, executor: PositionExecutor) -> bool:
        raise False

    def get_close_price(self, connector: str, trading_pair: str):
        """
        Gets the close price of the last candlestick.
        """
        candles = self.get_candles_by_connector_trading_pair(connector, trading_pair)
        first_candle = list(candles.values())[0]
        return first_candle.candles_df["close"].iloc[-1]

    def get_candles_with_price_and_spread_multipier(self):
        """
        Gets the price and spread multiplier from the last candlestick.
        """
        candles_df = self.candles[0].candles_df
        # macd = ta.macd(candles_df["close"], fast=self.config.macd_fast, slow=self.config.macd_slow, signal=self.config.macd_signal)
        # bbands = ta.bbands(candles_df["close"], length=self.config.bbands_length, std=self.config.bbands_std)
        # macd_standardized = (macd - macd.mean()) / macd.std()
        #
        # natr = ta.natr(candles_df["high"], candles_df["low"], candles_df["close"], length=self.config.natr_length)

        # candles_df["spread_multiplier"] = natr.iloc[-1]
        candles_df["spread_multiplier"] = 1
        candles_df["price_multiplier"] = 1
        return candles_df

    def get_price_and_spread_multiplier(self):
        """
        Gets the price and spread multiplier from the last candlestick.
        """
        candles_df = self.get_candles_with_price_and_spread_multipier()
        return candles_df["price_multiplier"].iloc[-1], candles_df["spread_multiplier"].iloc[-1]

    def get_position_config(self, order_level: OrderLevel) -> PositionConfig:
        """
        Creates a PositionConfig object from an OrderLevel object.
        Here you can use technical indicators to determine the parameters of the position config.
        """
        close_price = self.get_close_price(self.config.exchange, self.config.trading_pair)
        amount = order_level.order_amount_usd / close_price
        price_multiplier, spread_multiplier = self.get_price_and_spread_multiplier()

        price_adjusted = close_price * (1 + price_multiplier)
        side_multiplier = -1 if order_level.side == "buy" else 1
        order_price = price_adjusted * (1 + order_level.spread_factor * spread_multiplier * side_multiplier)

        position_config = PositionConfig(
            timestamp=time.time(),
            trading_pair=self.config.trading_pair,
            exchange=self.config.exchange,
            side=order_level.side,
            amount=amount,
            take_profit=order_level.take_profit,
            stop_loss=order_level.stop_loss,
            time_limit=order_level.time_limit,
            entry_price=Decimal(order_price),
            open_order_type=order_level.open_order_type,
            take_profit_order_type=order_level.take_profit_order_type,
            trailing_stop=TrailingStop(
                activation_price_delta=order_level.trailing_stop_activation_price_delta,
                trailing_delta=order_level.trailing_stop_trailing_delta,
            )
        )
        return position_config
