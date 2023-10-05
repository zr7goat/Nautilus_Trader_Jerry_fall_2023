import os, shutil
import pandas as pd
from decimal import Decimal
from nautilus_trader.model.data.tick import QuoteTick
from nautilus_trader.model.objects import Price, Quantity
from nautilus_trader.core.datetime import dt_to_unix_nanos
from nautilus_trader.persistence.catalog import ParquetDataCatalog
from nautilus_trader.persistence.external.core import process_files, write_objects
from nautilus_trader.persistence.external.readers import CSVReader
from nautilus_trader.test_kit.providers import TestInstrumentProvider



def parser(data, instrument_id):
    """
    Parser function for OKX Tick data, for use with CSV Reader
    Should check
    1) the data structure of the file
    2) “as_dataframe” true or false and
    use from_str for string data and from_int for int data and return a QuoteTick object

    """
    dt = pd.Timestamp(data['exchTimeMs'], unit='ms', tz='UTC')
    yield QuoteTick(
        instrument_id=instrument_id,
        bid=Price.from_str(str(data['bidPx1'])),
        ask=Price.from_str(str(data['askPx1'])),
        bid_size=Quantity.from_str(str(data['bidSz1'])),
        ask_size=Quantity.from_str(str(data['askSz1'])),
        ts_event=dt_to_unix_nanos(dt),
        ts_init=dt_to_unix_nanos(dt),
    )

input_files = r"D:\下载\BTC-USDT-220107.OK.csv"  # "your_path_to_file"
CATALOG_PATH = r"D:/backtest/backtest1/catalog_Sz_01"  # "your_path_to_catalog"
# Clear if it already exists, then create fresh
if os.path.exists(CATALOG_PATH):
    shutil.rmtree(CATALOG_PATH)
os.mkdir(CATALOG_PATH)
catalog = ParquetDataCatalog(CATALOG_PATH)  # Create a new ParquetDataCatalog instance

# # For DEFAULT nautilus-trader with default function btcusdt_future_binance in TestInstrumentProvider
# instrument = TestInstrumentProvider.btcusdt_future_binance()

# For EDITABLE nautilus-trader with customized function btcusdt_future_OKX in TestInstrumentProvider
# Use nautilus test helpers to create a BTC/USDT Crypto instrument for our purposes
maker1 = Decimal(-0.000001)
taker1 = Decimal(0.0000143)
instrument = TestInstrumentProvider.btcusdt_future_OKX(maker=maker1, taker=taker1)

# Add our new instrument to the ParquetDataCatalog and check its existence
write_objects(catalog, [instrument])
catalog.instruments()

# Loading the files (the header can be customized)
process_files(
    glob_path=input_files,
    reader=CSVReader(
        block_parser=lambda x: parser(x, instrument_id=instrument.id),
        header=None,
        chunked=False,
        as_dataframe=True,
    ),
    catalog=catalog,
)

# Also manually write the instrument to the catalog
write_objects(catalog, [instrument])

# Using the data Catalog
start = dt_to_unix_nanos(pd.Timestamp('2022-01-01', tz='UTC'))
end = dt_to_unix_nanos(pd.Timestamp('2022-01-01 23:00:00', tz='UTC'))

catalog.quote_ticks(start=start, end=end)