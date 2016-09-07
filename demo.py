from src.order_book import OrderBook

'''
Basic liquidity providing principles
'''

book = OrderBook()

# 0 0 0
print(book.ask_size, book.bid_size, book.total_volume_traded)

# LMT sell 10pcs @12.5
book.submit_order('lmt', 'ask', 10, 12.5, 1)

# LMT buy 10pcs @10.5
book.submit_order('lmt', 'bid', 10, 10.5, 2)

# 10 10 0
print(book.ask_size, book.bid_size, book.total_volume_traded)

# Satisfies market demand on both sides
book.submit_order('lmt', 'bid', 10, 20, 3)
book.submit_order('lmt', 'ask', 10, 5, 3)

# 0 0 20
print(book.ask_size, book.bid_size, book.total_volume_traded)

'''
Market microstructure
---
Implementation is not making concrete orders public
only order sizes on given level
'''

book = OrderBook()

# Get 5 levels of order book
# [[], []]
print(book.get_mkt_depth(5))

book.submit_order('lmt', 'ask', 2, 10, 1)
book.submit_order('lmt', 'ask', 4, 20, 1)
book.submit_order('lmt', 'ask', 6, 30, 1)

book.submit_order('lmt', 'bid', 1, 1, 2)
book.submit_order('lmt', 'bid', 5, 2, 2)
book.submit_order('lmt', 'bid', 7, 3, 2)

# [[[Price, Size] * n], [[Price, Size] * n]]
print(book.get_mkt_depth(3))

# ([IDs], [{ID: (size, side, priority_id)}])
# OrderBook respects time priority. It means that if
#  trader A submitted LMT buy @10 and trader B did same
#  then trader A is traded first
print(book.get_participant_orders(1))