import unittest
import random
import time
import pickle

import sys

sys.path.append('./')

from src.order_book import OrderBook

class OrderBookTest(unittest.TestCase):
    def test_submit_order(self):
        order_id = None
        updates = None

        ob = OrderBook()
        owner_id = 1

        try:
            order_id, updates = ob.submit_order('lmt', 'ask', 10, 125.12, owner_id)
        except:
            pass

        self.assertIsNotNone(order_id)
        self.assertIsNotNone(updates)
        self.assertListEqual(updates, [])

    def test_side_size_calculation(self):
        ask_ob = OrderBook()
        bid_ob = OrderBook()
        size_sum = 0

        sz = 0
        for i in range(random.randint(1E3, 1E4)):
            sz = random.randint(1, 10)

            ask_ob.submit_order('lmt', 'ask', sz, 1E6 - i, 1)
            bid_ob.submit_order('lmt', 'bid', sz, i, 1)

            size_sum += sz

        self.assertEqual(ask_ob.ask_size, sz)
        self.assertEqual(bid_ob.bid_size, sz)

        self.assertEqual(ask_ob.total_ask_size, size_sum)
        self.assertEqual(bid_ob.total_bid_size, size_sum)


    def test_lmt_same_price(self):
        ob = OrderBook()
        granulated_size = random.choice(['ask', 'bid'])
        price = random.randint(1, 1E3) / 10
        size_sum = 0
        for i in range(int(1E3)):
            sz = 2 * random.randint(1, 1E2)
            size_sum += sz

            if 'ask' == granulated_size:
                ob.submit_order('lmt', 'ask', sz, price, 1)
            else:
                ob.submit_order('lmt', 'bid', sz, price, 1)

        if 'ask' != granulated_size:
            ob.submit_order('lmt', 'ask', size_sum / 2, price, 1)

            self.assertEqual(ob.ask_size, 0)
            self.assertEqual(ob.total_ask_size, 0)

            self.assertEqual(ob.bid_size, size_sum / 2)
            self.assertEqual(ob.total_bid_size, size_sum / 2)
        else:
            ob.submit_order('lmt', 'bid', size_sum / 2, price, 1)

            self.assertEqual(ob.bid_size, 0)
            self.assertEqual(ob.total_bid_size, 0)

            self.assertEqual(ob.ask_size, size_sum / 2)
            self.assertEqual(ob.total_ask_size, size_sum / 2)

    def test_owner_matching(self):
        ob = OrderBook()
        bid_id, bid_trades = ob.submit_order('lmt', 'bid', 2, 2, 1)
        ask_id, ask_trades = ob.submit_order('lmt', 'ask', 2, 2, 2)

        # 0 - public message
        ask_owner = ask_trades[1][4] # Order which matched with existing goes first
        bid_owner = ask_trades[2][4]

        self.assertEqual(bid_id, bid_owner)
        self.assertEqual(ask_id, ask_owner)

    def test_ask_goes_first(self):
        ob = OrderBook()
        bid_id, bid_trades = ob.submit_order('lmt', 'bid', 2, 2, 1)
        ask_id, ask_trades = ob.submit_order('lmt', 'ask', 2, 2, 2)

        self.assertEqual(ask_trades[1][5], 'ask')
        self.assertEqual(ask_trades[2][5], 'bid')

    def test_get_orders(self):
        ob = OrderBook()

        ask_ids = []
        bid_id, bid_trades = ob.submit_order('lmt', 'bid', 2, 2, 1)

        ask_id, ask_trades = ob.submit_order('lmt', 'ask', 2, 3, 2)
        ask_ids.append(ask_id)

        ask_id, ask_trades = ob.submit_order('lmt', 'ask', 2, 3, 2)
        ask_ids.append(ask_id)

        ask_id, ask_trades = ob.submit_order('lmt', 'ask', 2, 3, 2)
        ask_ids.append(ask_id)

        self.assertListEqual(ask_ids, ob.get_participant_orders(2)[0])
        self.assertListEqual([bid_id], ob.get_participant_orders(1)[0])

    def test_persistence(self):
        ob_original = OrderBook()
        ob_recovered = OrderBook()

        price_levels = 0
        total_size = 0
        for price in range(random.randint(1E2, 1E3)):
            for size in range(random.randint(5, 15)):
                total_size += 2 * size

                ob_original.submit_order('lmt', 'bid', size, price, 1)
                ob_original.submit_order('lmt', 'ask', size, 1E6 - price, 1)

            price_levels += 1

        # started = time.time()
        ob_recovered = pickle.loads(pickle.dumps(ob_original))
        # print("Time to recover", price_levels, "price levels order book. With total size", total_size, time.time() - started)

        self.assertListEqual(ob_original.get_mkt_depth(price_levels), ob_recovered.get_mkt_depth(price_levels))
        self.assertEqual(ob_original.bid_size, ob_recovered.bid_size)
        self.assertEqual(ob_original.total_bid_size, ob_recovered.total_bid_size)

    def test_total_volume(self):
        ob = OrderBook()
        total_size = 0
        for price in range(random.randint(1E2, 1E3)):
            for size in range(random.randint(5, 15)):
                total_size += 2 * size

                ob.submit_order('lmt', 'bid', size, price, 1)
                ob.submit_order('lmt', 'ask', size, 1E6 - price, 1)

        self.assertEqual(ob.total_volume_pending, total_size)
        self.assertEqual(ob.total_volume_traded, 0)

        ob = OrderBook()
        ob.submit_order('lmt', 'bid', 1, 1, 1)
        ob.submit_order('lmt', 'ask', 1, 1, 1)

        self.assertEqual(ob.total_volume_traded, 1)
        self.assertEqual(ob.total_volume_pending, 0)

    def test_spread(self):
        ob = OrderBook()

        price = random.randint(1, 1E3)
        offset = random.randint(1, 1E3)

        # order_type, side, size, price, owner_id
        ob.submit_order('lmt', 'bid', 2, price, 5)
        ob.submit_order('lmt', 'ask', 2, price + offset, 5)

        self.assertEqual(ob.spread, offset)

    def test_performance(self):
        def test_struct(struct, method, test_rounds):
            times = []
            for i in range(int(test_rounds)):
                started = time.time()
                price = random.randint(1E2, 1E3) / 10
                size = random.randint(1E3, 1E4)
                side = random.choice(['ask', 'bid'])
                order_type = random.choice(['lmt', 'mkt'])

                if method == 'append':
                    struct.append((price, side))

                if method == 'submit_order':
                    struct.submit_order(order_type, side, size, price, 1)

                times.append(time.time() - started)

            return sum(times) / test_rounds

        for test_rounds in range(1, 5):
            ob_avg_t = test_struct(OrderBook(), 'submit_order', 10 ** test_rounds)
            list_avg_t = test_struct([], 'append', 10 ** test_rounds)

            #print('\n', 10 ** test_rounds, ob_avg_t, list_avg_t)

            self.assertLess(list_avg_t / ob_avg_t, 5)


if __name__ == '__main__':
    unittest.main()
