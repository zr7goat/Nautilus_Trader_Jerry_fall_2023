import pandas as pd

pd.set_option('display.max_columns', None)  # 显示所有列
pd.set_option('display.width', None)        # 确保每一列都能完全显示
pd.set_option('display.max_rows', None)     # 显示所有行
pd.set_option('display.max_colwidth', None) # 显示每一列的完整内容

filename = r"D:\backtest\backtest1\catalog_Sz_01\data\quote_tick.parquet\instrument_id=BTCUSDT_220325.OKX\1640995200008000000-1640997071853000000-0.parquet"
# Update the file extension to .parquet
data = pd.read_parquet(filename, engine='pyarrow')  # Use read_parquet instead of read_csv

print(data)
print(data.dtypes)  # 查看每一列的数据类型
print(data.head())  # 查看head
print(data.columns)  # 查看列名