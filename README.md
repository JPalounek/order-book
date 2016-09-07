## About
My implementation of Exchange Limit Orderbook I did for Prop trading department of the leading CEE investment bank. (NDA free part of bigger solution)

## What is OrderBook
The OrderBook is a place where orders get executed and where liquidity is made.

It's a core of every capital markets exchange and its simulation and modeling is an elementary step in market microstructure discovery what is a base for not only Structural arbitrage trading algorithms.

[Read more about OB at Investopedia](http://www.investopedia.com/terms/o/order-book.asp)

## Data structures used
Order data are stored in AVL trees - fast C language implementation of AVL trees (bintrees package). Update and search both have complexity of O(log n) thanks to this.

Multiple data redundancies are tolerated to achieve a maximal execution speed (for RT market structure simulation is speed crucial)

## Operations available

Checkout demo.py for brief introduction or unit test in folder tests.

book = OrderBook()

* submit_order(order_type, side, size, price, participant_id) - lmt/mkt is supported, ask/bid sides
* cancel(order_id)
* ask_size - on best ask level
* total_ask_size - over all levels
* -- same for bid --
* total_volume_traded
* total_volume_pending
* ask - best ask price
* bid - best bid price
* get_participant_orders(participant_id)
* get_mkt_depth(n) - returns n levels of order book

Order matching algorithm is executed after every order submit and executed orders are returned by submit_order function.

## Persistance

Persistance is done with pickle module (serializing processed data so no security risk at all). Whole OrderBook object is pickle serializable.