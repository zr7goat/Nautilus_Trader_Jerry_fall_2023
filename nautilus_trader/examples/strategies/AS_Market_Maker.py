# -------------------------------------------------------------------------------------------------
#  Copyright 2023 Jerry Li @ Positive Venture Group
#
#
#  This file is a template for Q-quant market making strategies as Avelleneda-Stoikov (AS) market maker.
#  This strategy is based on tick level data and is designed for HFT market making.
# -------------------------------------------------------------------------------------------------

from decimal import Decimal
from typing import Optional

from nautilus_trader.config import StrategyConfig
from nautilus_trader.model.data.tick import QuoteTick
from nautilus_trader.model.enums import BookType
from nautilus_trader.model.enums import OrderSide
from nautilus_trader.model.enums import TimeInForce
from nautilus_trader.model.enums import book_type_from_str
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.instruments.base import Instrument
from nautilus_trader.model.orderbook.book import OrderBook
from nautilus_trader.model.orderbook.data import BookOrder
from nautilus_trader.model.orderbook.data import OrderBookData
from nautilus_trader.trading.strategy import Strategy


# *** Avelleneda-Stoikov (AS) Market making model. ***
# *** In the initial model, it loses from trades themselves and profits from the maker transaction fee rebate. ***


class OrderBookImbalanceConfig(StrategyConfig):
    """
    Configuration for ``OrderBookImbalance`` instances.

    Parameters
    ----------
    instrument_id : InstrumentId
        The instrument ID for the strategy.
    max_trade_size : str
        The max position size per trade (volume on the level can be less).
    trigger_min_size : float
        The minimum size on the larger side to trigger an order.
    order_id_tag : str
        The unique order ID tag for the strategy. Must be unique
        amongst all running strategies for a particular trader ID.
    oms_type : OmsType
        The order management system type for the strategy. This will determine
        how the `ExecutionEngine` handles position IDs (see docs).
    book_type : BookType {``L1_TBBO``, ``L2_MBP``, ``L3_MBO``}
        The order book type to use for the strategy.
    use_quote_ticks : bool
        Whether to use quote ticks instead of order book data. When set to True,
        the strategy will use the  "L1_TBBO" orderbook and subscribe quotetick data
        no matter what the book_type is; When set to False, the strategy will use
        the book_type orderbook and subscribe to orderbook delta data
    subscribe_ticker : bool
        Whether to subscribe to ticker data. When set to True, the strategy will
        subscribe to ticker data in addition to the data source specified by book_type and use_quote_ticks.
    gamma : float
        The risk aversion parameter.
    Q: float
        The maximum position size.
    A： float
        The parameter of the exponential market speed function (y = A*np.exp(-k*x)).
    k: float
        The parameter of the number of times of the exponential market speed function.
    sigma: float
        The volotility (std) of the target price
    trade_interval: int
        The frequency of trading. The unit is ms
    fee_rate: float
        The transaction fee rate
    """

    instrument_id: str
    max_trade_size: Decimal
    trigger_min_size: float = 0.5
    trigger_imbalance_ratio: float = 0.4
    book_type: str = "L2_MBP"
    use_quote_ticks: bool = False
    subscribe_ticker: bool = False


class OrderBookImbalance(Strategy):
    """
    A simple strategy that sends FOK limit orders when there is a bid/ask
    imbalance in the order book.

    Cancels all orders and closes all positions on stop.

    Parameters
    ----------
    config : OrderbookImbalanceConfig
        The configuration for the instance.
    """

    def __init__(self, config: OrderBookImbalanceConfig):
        assert 0 < config.trigger_imbalance_ratio < 1
        super().__init__(config)

        # Configuration
        self.instrument_id = InstrumentId.from_str(config.instrument_id)
        self.max_trade_size = Decimal(config.max_trade_size)
        self.trigger_min_size = config.trigger_min_size
        self.trigger_imbalance_ratio = config.trigger_imbalance_ratio
        self.instrument: Optional[Instrument] = None
        if self.config.use_quote_ticks:
            assert self.config.book_type == "L1_TBBO"
        self.book_type: BookType = book_type_from_str(self.config.book_type)
        self._book = None  # type: Optional[OrderBook]

    def on_start(self):
        """Actions to be performed on strategy start."""
        self.instrument = self.cache.instrument(self.instrument_id)
        if self.instrument is None:
            self.log.error(f"Could not find instrument for {self.instrument_id}")
            self.stop()
            return

        if self.config.use_quote_ticks:
            book_type = BookType.L1_TBBO
            self.subscribe_quote_ticks(self.instrument.id)
        else:
            book_type = book_type_from_str(self.config.book_type)
            self.subscribe_order_book_deltas(self.instrument.id, book_type)
        if self.config.subscribe_ticker:
            self.subscribe_ticker(self.instrument.id)
        self._book = OrderBook.create(instrument=self.instrument, book_type=book_type)

    def on_order_book_delta(self, data: OrderBookData):
        """Actions to be performed when a delta is received."""
        if not self._book:
            self.log.error("No book being maintained.")
            return

        self._book.apply(data)
        if self._book.spread():
            self.check_trigger()

    def on_quote_tick(self, tick: QuoteTick):
        """Actions to be performed when a delta is received."""
        bid = BookOrder(
            price=tick.bid.as_double(),
            size=tick.bid_size.as_double(),
            side=OrderSide.BUY,
        )
        ask = BookOrder(
            price=tick.ask.as_double(),
            size=tick.ask_size.as_double(),
            side=OrderSide.SELL,
        )

        self._book.clear()
        self._book.update(bid)
        self._book.update(ask)
        if self._book.spread():
            self.check_trigger()

    def on_order_book(self, order_book: OrderBook):
        """Actions to be performed when an order book update is received."""
        self._book = order_book
        if self._book.spread():
            self.check_trigger()

    def check_trigger(self):
        """Check for trigger conditions."""
        if not self._book:
            self.log.error("No book being maintained.")
            return

        if not self.instrument:
            self.log.error("No instrument loaded.")
            return

        bid_size = self._book.best_bid_qty()
        ask_size = self._book.best_ask_qty()
        if not (bid_size and ask_size):
            return

        smaller = min(bid_size, ask_size)
        larger = max(bid_size, ask_size)
        ratio = smaller / larger
        self.log.info(
            f"Book: {self._book.best_bid_price()} @ {self._book.best_ask_price()} ({ratio=:0.4f})",  # ratio was 0.2 initially
        )
        if larger > self.trigger_min_size and ratio < self.trigger_imbalance_ratio:
            if len(self.cache.orders_inflight(strategy_id=self.id)) > 0:
                pass
            elif bid_size > ask_size:
                order = self.order_factory.limit(
                    instrument_id=self.instrument.id,
                    price=self.instrument.make_price(self._book.best_ask_price()),
                    order_side=OrderSide.BUY,
                    quantity=self.instrument.make_qty(ask_size),
                    post_only=False,
                    time_in_force=TimeInForce.FOK,
                )
                self.submit_order(order)
            else:
                order = self.order_factory.limit(
                    instrument_id=self.instrument.id,
                    price=self.instrument.make_price(self._book.best_bid_price()),
                    order_side=OrderSide.SELL,
                    quantity=self.instrument.make_qty(bid_size),
                    post_only=False,
                    time_in_force=TimeInForce.FOK,
                )
                self.submit_order(order)

    def on_stop(self):
        """Actions to be performed when the strategy is stopped."""
        if self.instrument is None:
            return
        self.cancel_all_orders(self.instrument.id)
        self.close_all_positions(self.instrument.id)
