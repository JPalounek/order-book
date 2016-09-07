from bintrees import FastAVLTree
import pickle

class OrderBook:
    """Limit order book able to process LMT and MKT orders
        MKT orders are disassembled to LMT orders up to current liquidity situation
    """

    def __init__(self):
        # AVL trees are used as a main structure due its optimal performance features for this purpose

        self._participants = FastAVLTree()
        self._order_owners = FastAVLTree() # Assigning ID -> Owner

        self._asks = FastAVLTree()  # MIN Heap
        self._bids = FastAVLTree()  # MAX Heap
        self._price_ids = FastAVLTree()  # Assigning ID -> Price

        self._total_ask_size = 0 # For monitoring purpose
        self._total_bid_size = 0 # For monitoring purpose

        self._last_order_id = 0 # Increases with each order processed
        self._cleared_orders_count = 0 # For monitoring purpose
        self._total_volume_traded = 0 # For monitoring purpose
        self._total_volume_pending = 0 # For monitoring purpose


    def __getstate__(self):
        """ Whole book could be repopulated from dict containing class attributes """

        return self.__dict__

    def __setstate__(self, state):
        """ Book repopulation (recovery) """

        for attr_name, attr_val in state.items():
            setattr(self, attr_name, attr_val)

    def _get_order_id(self):
        """ Orders id managment """

        self._last_order_id += 1
        return self._last_order_id

    def _balance(self, trades_stack):
        """ Executes trades if it finds liquidity for them """

        # No liquidity at all
        if self._asks.is_empty() or self._bids.is_empty():
            return trades_stack

        min_ask = self._asks.min_key()
        max_bid = self._bids.max_key()

        # Check liquidity situation
        if max_bid >= min_ask:
            ask_orders = self._asks.get(min_ask)
            bid_orders = self._bids.get(max_bid)

            for ask_order in ask_orders:
                for bid_order in bid_orders:
                    if not ask_order in ask_orders or not bid_order in bid_orders:
                        continue

                    traded = min(ask_orders[ask_order], bid_orders[bid_order])

                    ask_orders[ask_order] -= traded
                    bid_orders[bid_order] -= traded

                    self._total_ask_size -= traded
                    self._total_bid_size -= traded

                    self._total_volume_traded += traded
                    self._total_volume_pending -= 2 * traded

                    ask_owner = self._order_owners[ask_order]
                    bid_owner = self._order_owners[bid_order]

                    # Buy side order fully liquidated
                    if bid_orders[bid_order] == 0:
                        # print("BID ORDER LIQUIDATED")
                        self._cleared_orders_count += 1
                        del bid_orders[bid_order]
                        del self._price_ids[bid_order]

                        del self._order_owners[bid_order]
                        owner_ids = self._participants[bid_owner]
                        owner_ids.remove(bid_order)

                        del self._participants[bid_owner]
                        self._participants.insert(bid_owner, owner_ids)

                    # Sell side order fully liquidated
                    if ask_orders[ask_order] == 0:
                        # print("ASK ORDER LIQUIDATED")
                        self._cleared_orders_count += 1
                        del ask_orders[ask_order]
                        del self._price_ids[ask_order]

                        del self._order_owners[ask_order]
                        owner_ids = self._participants[ask_owner]
                        owner_ids.remove(ask_order)

                        del self._participants[ask_owner]
                        self._participants.insert(ask_owner, owner_ids)

                    # Inform sides about state of their orders
                    trades_stack.append((0, traded, max_bid))
                    trades_stack.append((1, ask_order, traded, max_bid, ask_owner, 'ask'))
                    trades_stack.append((1, bid_order, traded, max_bid, bid_owner, 'bid'))

            # Whole ASK price level were liquidated, remove it from three and let it rebalance
            if self._asks[min_ask].is_empty():
                # print("ASK level liquidated")
                del self._asks[min_ask]

            # Whole BID price level were liquidated, remove it from three and let it rebalance
            if self._bids[max_bid].is_empty():
                # print("BID level liquidated")
                del self._bids[max_bid]
        else:
            return trades_stack

        return self._balance(trades_stack)

    def _submit_mkt(self, side, size, participant_id):
        """ Find liquidity for mkt order - put multiple lmt orders to extract liquidity for order execution """

        orders_list = []
        trades_stack = []

        while size > 0:
            if side == 'ask':
                second_side_size = self.bid_size
                second_side_price = self.bid
            else:
                second_side_size = self.ask_size
                second_side_price = self.ask

            # We could only taky liquidity which exists
            trade_size = min([second_side_size, size])
            orders_list.append(self._submit_lmt(side, trade_size, second_side_price, participant_id))
            trades_stack = self._balance(trades_stack)

            size -= trade_size

        return 0, trades_stack


    def _submit_lmt(self, side, size, price, participant_id):
        """ Submits LMT order to book """

        # Assign order ID
        order_id = self._get_order_id()

        # Pending volume monitoring
        self._total_volume_pending += size
        self._price_ids.insert(order_id, (price, side))

        # Keep track of participant orders, book will be asked for sure
        if participant_id not in self._participants:
            self._participants.insert(participant_id, [order_id])
        else:
            owner_trades = self._participants.get(participant_id, [])
            owner_trades.append(order_id)

        self._order_owners.insert(order_id, participant_id)

        # Assign to right (correct) side
        if side == 'ask':
            self._total_ask_size += size
            ask_level = self._asks.get(price, FastAVLTree())
            ask_level.insert(order_id, size)

            if price not in self._asks:
                self._asks.insert(price, ask_level)
        else:  # bid
            self._total_bid_size += size
            bid_level = self._bids.get(price, FastAVLTree())
            bid_level.insert(order_id, size)

            if price not in self._bids:
                self._bids.insert(price, bid_level)

        return order_id

    def cancel(self, order_id):
        """ Cancel order """

        # Finds and cancels order

        order = self._price_ids[order_id]

        if order[1] == 'ask':
            del self._asks[order[0]][order_id]

            if self._asks[order[0]].is_empty():
                del self._asks[order[0]]
        else:
            del self._bids[order[0]][order_id]

            if self._bids[order[0]].is_empty():
                del self._bids[order[0]]

    @property
    def ask_size(self):
        """ Volume waiting on ask side bottom level - liquidity level size for ask price """

        best_ask = self.get_mkt_depth(1)[0]

        if len(best_ask) == 0:
            return 0
        else:
            return best_ask[0][1]

    @property
    def total_ask_size(self):
        return self._total_ask_size

    @property
    def bid_size(self):
        """ Volume waiting on bid side top level - liquidity level size for bid price """

        best_bid = self.get_mkt_depth(1)[1]
        if len(best_bid) == 0:
            return 0
        else:
            return best_bid[0][1]

    @property
    def total_volume_traded(self):
        """ Total traded volume """

        return self._total_volume_traded

    @property
    def total_volume_pending(self):
        """ Total size of orders in whole book """

        return self._total_volume_pending

    @property
    def total_bid_size(self):
        return self._total_bid_size

    @property
    def ask(self):
        """ Best ask """

        try:
            return self.get_mkt_depth(1)[0][0][0]
        except:
            return -1

    @property
    def bid(self):
        """ Best bid """

        try:
            return self.get_mkt_depth(1)[1][0][0]
        except:
            return -1

    @property
    def spread(self):
        """ Difference between ask and bid """

        return self.ask - self.bid

    def get_participant_orders(self, participant_id):
        """ Orders of given participant """

        orders_list = self._participants.get_value(participant_id)

        order_prices = {}
        for order_id in orders_list:
            order = self._price_ids.get_value(order_id)

            if order[1] == 'ask':
                order_size = self._asks.get_value(order[0]).get_value(order_id)
            else:
                order_size = self._bids.get_value(order[0]).get_value(order_id)

            # price, side, size
            order_prices[order_id] = (order[0], order[1], order_size)

        return orders_list, order_prices

    def submit_order(self, order_type, side, size, price, participant_id):
        """ Abstraction on order placement - boht LMT and MKT """

        if order_type == 'lmt':
            order_id = self._submit_lmt(side, size, price, participant_id)
            trades = self._balance([])
            return order_id, trades

        if order_type == 'mkt':
            second_side_ask = 0
            if side != 'ask':
                second_side_ask = self._total_ask_size
            else:
                second_side_ask = self._total_bid_size

            if second_side_ask >= size:
                return self._submit_mkt(side, size, participant_id)
            else:
                # Insufficient liquidity
                return -1, []

    def get_mkt_depth(self, depth):
        """ Liquidity levels size for both bid and ask """

        ask_side = []
        if not self._asks.is_empty():
            for price in self._asks.keys():
                ask_level = self._asks.get(price)
                ask_size = 0
                for order_id in ask_level.keys():
                    # print(ask_size, order_id, ask_level.get(order_id))
                    ask_size += ask_level.get(order_id)

                ask_side.append([price, ask_size])

                if len(ask_side) >= depth:
                    break

        bid_side = []
        if not self._bids.is_empty():
            for price in self._bids.keys(reverse=True):
                bid_level = self._bids.get(price)
                bid_size = 0
                for order_id in bid_level.keys():
                    bid_size += bid_level.get(order_id)

                bid_side.append([price, bid_size])

                if len(bid_side) >= depth:
                    break

        return [ask_side, bid_side]
