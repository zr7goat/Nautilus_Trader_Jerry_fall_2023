#!/usr/bin/env python3
# -------------------------------------------------------------------------------------------------
# This file is a backtest file with imported catalog quote tick data of OKX
# This file is using BacktestNode to run the backtest
# Customized by Jerry based on exmaples\notebooks\external_data_backtest.ipynb
# -------------------------------------------------------------------------------------------------

import time
from decimal import Decimal

import pandas as pd

from nautilus_trader.backtest.node import BacktestNode
from nautilus_trader.core.datetime import dt_to_unix_nanos
from nautilus_trader.config import BacktestRunConfig, BacktestVenueConfig, BacktestDataConfig, BacktestEngineConfig
from nautilus_trader.config import ImportableStrategyConfig
from nautilus_trader.config import LoggingConfig
from nautilus_trader.config.common import ImportableStrategyConfig
from nautilus_trader.model.data.tick import QuoteTick
from nautilus_trader.persistence.catalog import ParquetDataCatalog


if __name__ == "__main__":

    # Using the data Catalog
    # catalog = ParquetDataCatalog.from_env()  # Create a new ParquetDataCatalog instance from the environment
    # ran on 08/28/23 Mon 14:50:00 but failed with no [Nautilus_Path]
    CATALOG_PATH = "D:/backtest/backtest1/catalog_Sz_01"  # "your_path_to_catalog"
    catalog = ParquetDataCatalog(CATALOG_PATH)  # Create a new ParquetDataCatalog instance
    catalog.instruments()  # List all instruments in the catalog

    start = dt_to_unix_nanos(pd.Timestamp('2022-01-01', tz='UTC'))
    end = dt_to_unix_nanos(pd.Timestamp('2022-01-01 23:00:00', tz='UTC'))

    catalog.quote_ticks(start=start, end=end)

    # Add instruments
    instrument = catalog.instruments(as_nautilus=True)[0]

    # Add a trading venue (multiple venues possible)
    venues_config = [
        BacktestVenueConfig(
            name="OKX",
            oms_type="HEDGING",
            account_type="MARGIN",
            base_currency="USDT",
            starting_balances=["1000000 USDT"],
        )
    ]

    # Add data
    data_config = [
        BacktestDataConfig(
            catalog_path=str(catalog.path),
            data_cls=QuoteTick,
            instrument_id=instrument.id.value,
            start_time=pd.Timestamp("2022-01-01").value,
            end_time=pd.Timestamp("2022-01-01 00:00:30").value,
        )
    ]

    # Configure your strategy
    strategies = [
        ImportableStrategyConfig(
            strategy_path="nautilus_trader.examples.strategies.orderbook_imbalance:OrderBookImbalance",
            config_path="nautilus_trader.examples.strategies.orderbook_imbalance:OrderBookImbalanceConfig",
            config=dict(
                instrument_id=instrument.id.value,
                max_trade_size=Decimal(1000),
                use_quote_ticks=True,
                trigger_min_size=0.5,
                trigger_imbalance_ratio=0.4,
                book_type="L1_TBBO",
                # order_id_tag=instrument.selection_id,
                # AttributeError: 'nautilus_trader.model.instruments.crypto_future.Cr' object has no attribute 'selection_id'
            ),
        ),
    ]

    config = BacktestRunConfig(
        engine=BacktestEngineConfig(
            strategies=strategies,
            logging=LoggingConfig(log_level="ERROR"),
        ),
        data=data_config,
        venues=venues_config,
    )

    node = BacktestNode(configs=[config])  # successfully ran but no reports

    results = node.run()
    print(results)
