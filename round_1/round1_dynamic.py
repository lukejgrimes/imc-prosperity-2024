from datamodel import OrderDepth, UserId, TradingState, Order
from typing import List
import pandas as pd
import numpy as np
import math
from collections import deque

AMETHYSTS = "AMETHYSTS"
STARFRUIT = "STARFRUIT"
historic_ameth_mean = 10000

position_limits = {
    AMETHYSTS: 20,
    STARFRUIT: 20
}

class Trader:
    def __init__(self):
        self.star_last_price = 5051
        self.star_returns = deque([-1.5, 2.5, -4.0, 1.5])
        self.star_price_window = deque([5051, 5053, 5049, 5051])
        self.star_errors_window = deque([0])
        self.star_preds_window = deque([1.5])

    def run(self, state: TradingState):
        ameth_position = state.position.get(AMETHYSTS, 0)
        ameth_max_buy_vol = position_limits[AMETHYSTS] - ameth_position
        ameth_max_sell_vol = -position_limits[AMETHYSTS] - ameth_position
        ameth_bids = state.order_depths[AMETHYSTS].buy_orders
        ameth_asks = state.order_depths[AMETHYSTS].sell_orders
        if len(ameth_bids) > 0:
            best_ameth_bid = list(ameth_bids.keys())[0]
        if len(ameth_asks) > 0:
            best_ameth_ask = list(ameth_asks.keys())[0]

        ameth_spread = best_ameth_ask - best_ameth_bid
        ameth_orders = []
        if best_ameth_ask < historic_ameth_mean:
            ameth_orders.append(Order(AMETHYSTS, best_ameth_ask, ameth_max_buy_vol))
        elif best_ameth_bid > historic_ameth_mean:
            ameth_orders.append(Order(AMETHYSTS, best_ameth_bid, ameth_max_sell_vol))
        elif ameth_spread >= 5:
            ameth_orders.append(Order(AMETHYSTS, best_ameth_bid + 1, ameth_max_buy_vol))
            ameth_orders.append(Order(AMETHYSTS, best_ameth_ask - 1, ameth_max_sell_vol))

        cur_star_pos = state.position.get(STARFRUIT, 0)
        star_max_buy_vol = position_limits[STARFRUIT] - cur_star_pos
        star_max_sell_vol = -position_limits[STARFRUIT] - cur_star_pos
        
        star_bids = state.order_depths[STARFRUIT].buy_orders
        star_asks = state.order_depths[STARFRUIT].sell_orders
        if len(star_bids) > 0:
            best_star_bid = list(star_bids.keys())[0]
        if len(star_asks) > 0:
            best_star_ask = list(star_asks.keys())[0]

        star_spread = best_star_ask - best_star_bid
        star_mid = round((best_star_bid + best_star_ask) / 2)

        self.star_price_window.append(star_mid)
        if len(self.star_price_window) > 4:
            self.star_price_window.popleft()

        
        star_ma = sum(list(self.star_price_window)) / len(self.star_price_window)
        
        ret = star_mid - self.star_last_price
        self.star_returns.append(ret)

        print(f"Pred Error: {self.star_returns[-1] - self.star_preds_window[-1]}")

        next_return = self.predict_next_price() if len(self.star_returns) >= 4 else ret
        self.star_preds_window.append(next_return)
        if len(self.star_preds_window) > 4:
            self.star_preds_window.popleft()

        next_price = round(star_mid + next_return)
        print(f"Last Price: {self.star_last_price}")
        print(f"Cur Price: {star_mid}")
        print(f"Next Price: {next_price}")
        self.star_last_price = star_mid

        print(state.position)

        star_orders = []
        if best_star_bid > next_price:
            star_orders.append(Order(STARFRUIT, best_star_bid - 1, star_max_sell_vol))
        elif best_star_ask < next_price:
            star_orders.append(Order(STARFRUIT, best_star_ask + 1, star_max_buy_vol))
        elif best_star_bid > star_ma:
            star_orders.append(Order(STARFRUIT, best_star_bid - 1, star_max_sell_vol))
        elif best_star_ask < star_ma:
            star_orders.append(Order(STARFRUIT, best_star_ask + 1, star_max_buy_vol))
        elif star_spread >= 5:
            star_orders.append(Order(STARFRUIT, best_star_bid + 1, star_max_buy_vol))
            star_orders.append(Order(STARFRUIT, best_star_ask - 1, star_max_sell_vol))

            
        result = {AMETHYSTS: ameth_orders,
                  STARFRUIT: star_orders}
        
        print(result)

        conversions = None
        traderData = ""

        return result, conversions, traderData
    
    def predict_next_price(self):
        Y = np.array(list(self.star_returns)[4:])
        X = np.vstack([np.array(list(self.star_returns)[i:len(self.star_returns) -4 + i]) for i in range(4)]).T

        coef = np.linalg.lstsq(X, Y, rcond=None)[0]
        next_return = coef @ list(self.star_returns)[-4:]
        return next_return
    