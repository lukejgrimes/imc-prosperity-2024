from datamodel import TradingState, Order
from collections import deque
import numpy as np

ORCHIDS = "ORCHIDS"
CHOCOLATE = "CHOCOLATE"
STRAWBERRIES = "STRAWBERRIES"
ROSES = "ROSES"
GIFT_BASKET = "GIFT_BASKET"
COMBO = "COMBO"

position_limits = {
    CHOCOLATE: 250,
    STRAWBERRIES: 350,
    ROSES: 60,
    GIFT_BASKET: 60,
    COMBO: 58
}

MAX_CHOCOLATE = 232
MAX_STRAWBERRIES = 348
MAX_ROSES = 58
MAX_BASKET = 58

class Trader:
    def __init__(self):
        pass
    def run(self, state: TradingState):

        chocolate_bids = state.order_depths[CHOCOLATE].buy_orders
        chocolate_asks = state.order_depths[CHOCOLATE].sell_orders
        best_choc_bid = list(chocolate_bids)[0]
        best_choc_ask = list(chocolate_asks)[0]
        chocolate_mid = best_choc_bid + (best_choc_ask - best_choc_bid) / 2

        strawberry_bids = state.order_depths[STRAWBERRIES].buy_orders
        strawberry_asks = state.order_depths[STRAWBERRIES].sell_orders
        best_straw_bid = list(strawberry_bids)[0]
        best_straw_ask = list(strawberry_asks)[0]
        straw_mid = best_straw_bid + (best_straw_ask - best_straw_bid) / 2

        rose_bids = state.order_depths[ROSES].buy_orders
        rose_asks = state.order_depths[ROSES].sell_orders
        best_rose_bid = list(rose_bids)[0]
        best_rose_ask = list(rose_asks)[0]
        rose_mid = best_rose_bid + (best_rose_ask - best_rose_bid) / 2

        basket_bids = state.order_depths[GIFT_BASKET].buy_orders
        basket_asks = state.order_depths[GIFT_BASKET].sell_orders
        best_basket_bid = list(basket_bids)[0]
        best_basket_ask = list(basket_asks)[0]
        basket_mid = best_basket_bid + (best_basket_ask - best_basket_bid) / 2

        Y = 6 * straw_mid + 4 * chocolate_mid + rose_mid
        spread = basket_mid - Y

        choc_position = state.position.get(CHOCOLATE, 0)
        straw_position = state.position.get(STRAWBERRIES, 0)
        rose_position = state.position.get(ROSES, 0)
        basket_position = state.position.get(GIFT_BASKET, 0)

        items_position = 4 * choc_position + 6 * straw_position + rose_position

        chocolate_orders = []
        strawberry_orders = []
        rose_orders = []
        basket_orders = []

        if spread >= 455:
            if items_position != position_limits[COMBO]:
                chocolate_orders.append(Order(CHOCOLATE, best_choc_ask, MAX_CHOCOLATE - choc_position))
                strawberry_orders.append(Order(STRAWBERRIES, best_straw_ask, MAX_STRAWBERRIES - straw_position))
                rose_orders.append(Order(ROSES, best_rose_ask, MAX_ROSES - rose_position))
            
            if basket_position != -MAX_BASKET:
                basket_orders.append(Order(GIFT_BASKET, best_basket_bid, -MAX_BASKET - basket_position))
        
        elif spread <= 305:
            if items_position != -position_limits[COMBO]:
                chocolate_orders.append(Order(CHOCOLATE, best_choc_bid, -MAX_CHOCOLATE - choc_position))
                strawberry_orders.append(Order(STRAWBERRIES, best_straw_bid, -MAX_STRAWBERRIES - straw_position))
                rose_orders.append(Order(ROSES, best_rose_bid, -MAX_ROSES - rose_position))
            
            if basket_position != MAX_BASKET:
                basket_orders.append(Order(GIFT_BASKET, best_basket_ask, MAX_BASKET - basket_position))

        result = {
            CHOCOLATE: chocolate_orders,
            STRAWBERRIES: strawberry_orders,
            ROSES: rose_orders,
            GIFT_BASKET: basket_orders
        }

        conversions = None
        traderData = ""

        return result, conversions, traderData
        