import pandas as pd
from nautilus_trader.core.datetime import dt_to_unix_nanos

# timestamp_ns = pd.Timestamp("2022-01-01").value
# print(timestamp_ns)
# start = dt_to_unix_nanos(pd.Timestamp('2022-01-01', tz='UTC'))
# print(start)
# end_time=pd.Timestamp("2022-01-01 23:00:00").value
# print(end_time)
# 设置显示选项
pd.set_option('display.max_columns', None)  # 显示所有列
pd.set_option('display.width', None)        # 确保每一列都能完全显示
pd.set_option('display.max_rows', None)     # 显示所有行
pd.set_option('display.max_colwidth', None) # 显示每一列的完整内容

# filename = r"D:\下载\DAT_ASCII_EURUSD_T_202308.csv"
# filename = r"D:\下载\BTC-USDT-220107.OK.csv"
# filename = r"D:\下载\LDOBUSD-bookTicker-2023-06\LDOBUSD-bookTicker-2023-06.csv"
filename = r"D:\下载\BTCUSDT-bookTicker-2023-09-17\BTCUSDT-bookTicker-2023-09-17.csv"
data = pd.read_csv(filename, nrows=10000)
data['spread'] = data['best_ask_price'] - data['best_bid_price']
data['midprice'] = (data['best_ask_price'] + data['best_bid_price']) / 2
data['midprice_change'] = data['midprice'].diff()
data['imbalance_-1to1'] = -data['best_ask_qty'] + data['best_bid_qty'] / data['best_ask_qty'] + data['best_bid_qty']  # 取值是-1到1之间，-1表示完全由卖单构成，1表示完全由买单构成
data['imbalance_0to1'] = data['best_ask_qty'] / data['best_ask_qty'] + data['best_bid_qty']  # 取值是0到1之间，0表示完全由卖单构成，1表示完全由买单构成
data['wmp'] = data['midprice'] + data['spread'] * data['imbalance_-1to1']/2
data['wmp_change'] = data['wmp'].diff()
data['dmp'] = data['midprice'] + data['spread'] * data['imbalance_-1to1'] * (data['imbalance_-1to1'] * data['imbalance_-1to1'] + 1) / 2  # 尚未完成，需要结合DMP公式考虑fee

print(data)
print(data.dtypes)  # 查看每一列的数据类型
print(data.head())  # 查看head
print(data.columns)  # 查看列名
#
# # pd.reset_option('display.max_columns')

