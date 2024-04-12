from datamodel import TradingState, Listing, OrderDepth, Trade, Observation, Order
from collections import deque
from typing import Dict, Deque
import pandas as pd
import numpy as np
from round1_kalman import Trader

STARFRUIT = "STARFRUIT"
AMETHYSTS = "AMETHYSTS"
SEASHELLS = "SEASHELLS"

class DetailedOrder:
    def __init__(self, order: Order, trader_id: str, order_id: int):
        self.order = order
        self.trader_id = trader_id
        self.order_id = order_id

class OrderBook:
    def __init__(self):
        self.bids: Dict[int, Deque[DetailedOrder]] = {}
        self.asks: Dict[int, Deque[DetailedOrder]] = {}

class MatchingEngine:
    def __init__(self, trader, data, bot_trades, iterations):

        self.state = TradingState(
            "", 0, 
            {STARFRUIT: Listing(STARFRUIT, STARFRUIT, SEASHELLS),
             AMETHYSTS: Listing(AMETHYSTS, AMETHYSTS, SEASHELLS)},
            {STARFRUIT: OrderDepth(), AMETHYSTS: OrderDepth()},
            {STARFRUIT: [], AMETHYSTS: []}, {STARFRUIT: [], AMETHYSTS: []},
            {STARFRUIT: 0, AMETHYSTS: 0}, Observation({}, {})
        )
        self.trader = trader
        self.order_books = {STARFRUIT: OrderBook(), AMETHYSTS: OrderBook()}
        self.order_count = 0
        self.position_limits = {STARFRUIT: 20, AMETHYSTS: 20}
        self.timestamp = 0
        self.data = data
        self.bot_trades = bot_trades
        self.pnl = {STARFRUIT: 0, AMETHYSTS: 0}
        self.num_timestamps = iterations * 100

    def run_iteration(self):
        self.get_bot_quotes()
        self.run_algo()
        self.get_bot_trades()
        self.update_pnl()

        if self.timestamp == self.num_timestamps - 100:
            self.settle_position()
            return self.pnl
        # Clear Order Books
        self.order_books = {STARFRUIT: OrderBook(), AMETHYSTS: OrderBook()}
        self.state.order_depths = {STARFRUIT: OrderDepth(), AMETHYSTS: OrderDepth()}
        self.timestamp += 100

    def match_orders(self, orders: Dict, algo: bool):
        trader_id = "SUBMISSION" if algo else ""
        for product in orders.keys():
            bids = self.order_books[product].bids
            asks = self.order_books[product].asks
            simple_bids = self.state.order_depths[product].buy_orders
            simple_asks = self.state.order_depths[product].sell_orders
            market_trades = []
            algo_trades = []
            cur_orders = deque(orders[product])
            while cur_orders:
                order: Order = cur_orders.popleft()
                self.order_count += 1
                price = order.price
                quantity = order.quantity
                remainder = quantity
                while remainder > 0 and asks and price >= min(asks.keys()):
                    best_ask = min(asks.keys())
                    if not asks[best_ask]:
                        del asks[best_ask]
                        continue
                    next_ask_order = asks[best_ask].popleft()
                    if not next_ask_order:
                        break
                    next_ask_quantity = next_ask_order.order.quantity
                    seller = next_ask_order.trader_id
                    fill_q = min(-next_ask_quantity, remainder)
                    if remainder < -next_ask_quantity:
                        next_ask_order.order.quantity += fill_q
                        asks[best_ask].appendleft(next_ask_order)

                    remainder = remainder - fill_q
                    buyer = trader_id
                    seller = next_ask_order.trader_id
                    trade = Trade(product, best_ask, fill_q, buyer, seller, self.state.timestamp)

                    if algo or seller == "SUBMISSION":
                        algo_trades.append(trade)
                        current_position = self.state.position[product]
                        self.state.position[product] = current_position + fill_q if algo else current_position - fill_q
                    else:
                        market_trades.append(trade)

                    simple_asks[best_ask] += fill_q
                    if simple_asks[best_ask] == 0:
                        del asks[best_ask]
                        del simple_asks[best_ask]

                if remainder > 0:
                    simple_bids[price] = simple_bids.get(price, 0) + remainder
                    self.order_count += 1
                    new_order = DetailedOrder(Order(product, price, remainder), trader_id, self.order_count)
                    if price in bids:
                        bids[price].appendleft(new_order)
                    else:
                        bids[price] = deque([new_order])
                    remainder = 0

                while remainder < 0 and bids and price <= max(bids.keys()):
                    best_bid = max(bids.keys())
                    if not bids[best_bid]:
                        del bids[best_bid]
                        continue
                    next_bid_order = bids[best_bid].popleft()
                    next_bid_quantity = next_bid_order.order.quantity
                    buyer = next_bid_order.trader_id
                    fill_q = min(next_bid_quantity, -remainder)
                    if -remainder < next_bid_quantity:
                        next_bid_order.order.quantity -= fill_q
                        bids[best_bid].appendleft(next_bid_order)

                    remainder = remainder + fill_q
                    buyer = next_bid_order.trader_id
                    seller = trader_id
                    trade = Trade(product, best_bid, fill_q, buyer, seller, self.state.timestamp)

                    if algo or buyer == "SUBMISSION":
                        algo_trades.append(trade)
                        current_position = self.state.position[product]
                        self.state.position[product] = current_position - fill_q if algo else current_position + fill_q
                    else:
                        market_trades.append(trade)

                    simple_bids[best_bid] -= fill_q
                    if simple_bids[best_bid] == 0:
                        del bids[best_bid]
                        del simple_bids[best_bid]

                if remainder < 0:
                    simple_asks[price] = simple_asks.get(price, 0) + remainder
                    self.order_count += 1
                    new_order = DetailedOrder(Order(product, price, remainder), trader_id, self.order_count)
                    if price in asks:
                        asks[price].appendleft(new_order)
                    else:
                        asks[price] = deque([new_order])
                    remainder = 0
            
            if algo:
                self.state.own_trades[product] = algo_trades
            else:
                self.state.market_trades[product] = market_trades
                self.state.own_trades[product] += algo_trades

    def run_algo(self):
        for product in self.state.order_depths.keys():
            bids = self.state.order_depths[product].buy_orders
            asks = self.state.order_depths[product].sell_orders
            self.state.order_depths[product].buy_orders = dict(sorted(bids.items(), key=lambda x: x[0], reverse=True))
            self.state.order_depths[product].sell_orders = dict(sorted(asks.items(), key=lambda x: x[0]))

        result, conversions, traderData = self.trader.run(self.state)
        for product in result.keys():
            total_buy_q = 0
            total_ask_q = 0
            valid_bids = []
            valid_asks = []
            for order in result[product]:
                if order.quantity > 0:
                    total_buy_q += order.quantity
                    valid_bids.append(order)
                elif order.quantity < 0:
                    total_ask_q += order.quantity
                    valid_asks.append(order)
                
            if total_buy_q + self.state.position[product] > self.position_limits[product]:
                valid_bids = []
            if total_ask_q + self.state.position[product] < -self.position_limits[product]:
                valid_asks = []

            result[product] = valid_bids + valid_asks
        # Clear Trade History
        self.state.market_trades = {STARFRUIT: [], AMETHYSTS: []}
        self.state.own_trades = {STARFRUIT: [], AMETHYSTS: []}
        self.match_orders(result, algo=True)

    def get_bot_quotes(self):
        quotes = self.data[self.data["timestamp"] == self.timestamp]
        for i in range(len(quotes)):
            row = quotes.iloc[i]
            product = row["product"]
            bids = [(row["bid_price_1"], row["bid_volume_1"]), (row["bid_price_2"], row["bid_volume_2"]), (row["bid_price_3"], row["bid_volume_3"])]
            asks = [(row["ask_price_1"], row["ask_volume_1"]), (row["ask_price_2"], row["ask_volume_2"]), (row["ask_price_3"], row["ask_volume_3"])]
            buy_order_depth = {}
            sell_order_depth = {}
            for bid in bids:
                price, quantity = bid
                if price > 0:
                    self.order_count += 1
                    order = DetailedOrder(Order(product, price, quantity), "", self.order_count)
                    self.order_books[product].bids.get(price, deque([])).append(order)
                    buy_order_depth[price] = buy_order_depth.get(price, 0) + quantity
            for ask in asks:
                price, quantity = ask
                if price > 0:
                    self.order_count += 1
                    order = DetailedOrder(Order(product, price, -quantity), "", self.order_count)
                    self.order_books[product].asks.get(price, deque([])).append(order)
                    sell_order_depth[price] = sell_order_depth.get(price, 0) - quantity

            self.state.order_depths[product].buy_orders = buy_order_depth
            self.state.order_depths[product].sell_orders = sell_order_depth

    def get_bot_trades(self):
        bot_orders = {STARFRUIT: [], AMETHYSTS: []}
        trades = self.bot_trades[self.bot_trades["timestamp"] == self.timestamp]
        for i in range(len(trades)):
            trade = trades.iloc[i]
            product = trade["symbol"]
            price = trade["price"]
            quantity = trade["quantity"]

            available_bids = self.order_books[product].bids.keys()
            available_asks = self.order_books[product].asks.keys()

            buy_order = Order(product, price, quantity)
            sell_order = Order(product, price, -quantity)

            if price in available_bids:
                bot_orders[product].append(sell_order)
            elif price in available_asks:
                bot_orders[product].append(buy_order)
            else:
                bot_orders[product].append(sell_order)
                bot_orders[product].append(buy_order)
                
        self.match_orders(bot_orders, algo=False)

    def update_pnl(self):
        print(self.timestamp)
        trades = self.state.own_trades
        for product in trades.keys():
            for trade in trades[product]:
                self.pnl[product] += (trade.price * trade.quantity) if trade.seller else (trade.price * -trade.quantity)

            best_bid = max(self.state.order_depths[product].buy_orders.keys())
            best_ask = min(self.state.order_depths[product].sell_orders.keys())
            position = self.state.position[product]
            cur_profit = self.pnl[product] + (position * best_bid) if position >= 0 else self.pnl[product] + (position * best_ask)

    def settle_position(self):
        for product in self.pnl:
            best_bid = max(self.state.order_depths[product].buy_orders.keys())
            best_ask = min(self.state.order_depths[product].sell_orders.keys())
            position = self.state.position[product]
            self.pnl[product] += position * best_bid if position >= 0 else position * best_ask
            print(f"{product} Profit/Loss: {self.pnl[product]}")
        

def backtest(iterations, trader, data, bot_trades):
    data = pd.read_csv(data, delimiter=';')
    bot_trades = pd.read_csv(bot_trades, delimiter=";")
    engine = MatchingEngine(trader, data, bot_trades, iterations)
    for _ in range(iterations):
        profit = engine.run_iteration()
        
    return profit

if __name__ == "__main__":
    trader = Trader()
    backtest(10000, trader, "./round-1-island-data-bottle/prices_round_1_day_-1.csv", "./round-1-island-data-bottle/trades_round_1_day_-1_nn.csv")
