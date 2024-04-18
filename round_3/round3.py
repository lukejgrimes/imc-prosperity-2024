from datamodel import TradingState, Order
from collections import deque
import numpy as np

AMETHYSTS = "AMETHYSTS"
STARFRUIT = "STARFRUIT"
ORCHIDS = "ORCHIDS"
CHOCOLATE = "CHOCOLATE"
STRAWBERRIES = "STRAWBERRIES"
ROSES = "ROSES"
GIFT_BASKET = "GIFT_BASKET"
COMBO = "COMBO"

MAX_CHOCOLATE = 232
MAX_STRAWBERRIES = 348
MAX_ROSES = 58
MAX_BASKET = 58

historic_ameth_mean = 10000

position_limits = {
    AMETHYSTS: 20,
    STARFRUIT: 20,
    ORCHIDS: 100,
    CHOCOLATE: 250,
    STRAWBERRIES: 350,
    ROSES: 60,
    GIFT_BASKET: 60,
    COMBO: 58
}

class Trader:
    def __init__(self):
        self.star_last_price = None
        self.star_returns = deque([])
        self.star_price_window = deque([])
        self.star_last_error = 0
        self.star_last_prediction = None

        self.orchid_last_price = None

    def run(self, state: TradingState):
        print(state.position)

        star_orders = self.starfruit_strategy(state)
        ameth_orders = self.amethysts_strategy(state)
        orchid_orders, conversions = self.orchids_strategy(state)
        pairs_orders = self.baskets_strategy(state)
        chocolate_orders = pairs_orders[CHOCOLATE]
        strawberry_orders = pairs_orders[STRAWBERRIES]
        rose_orders = pairs_orders[ROSES]
        basket_orders = pairs_orders[GIFT_BASKET]

        result = {
            AMETHYSTS: ameth_orders,
            STARFRUIT: star_orders,
            ORCHIDS: orchid_orders,
            CHOCOLATE: chocolate_orders,
            STRAWBERRIES: strawberry_orders,
            ROSES: rose_orders,
            GIFT_BASKET: basket_orders
        }
        
        print(result)

        traderData = ""

        return result, conversions, traderData
    
    
    def predict_starfruit_return(self):
        coef = [-0.015737, -0.021336, -0.022084, -0.030806]
        err_coef = -0.677231
        next_return = 0.001694

        for i in range(len(coef)):
            next_return += coef[i] * self.star_returns[i]

        next_return += self.star_last_error * err_coef
        return next_return
    
    def predict_orchid_price(self, last_price, sunlight, humidity):
        coef = [0.9996717565693496, 1.1443871506246691e-05, 0.0010130090910631384]
        next_price = 0.24488328854047636

        X = np.column_stack([last_price, sunlight, humidity])
        coef = np.reshape(coef, (1, 3))
        next_price = next_price + coef @ X.T

        return next_price
    
    def starfruit_strategy(self, state: TradingState):
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

        
        star_ma = np.mean(list(self.star_price_window))
        
        ret = star_mid - self.star_last_price if self.star_last_price else 0
        self.star_returns.append(ret)

        self.star_last_error = self.star_returns[-1] - self.star_last_prediction if self.star_returns and self.star_last_prediction else 0

        if len(self.star_returns) > 4:
            self.star_returns.popleft()

        next_return = self.predict_starfruit_return() if len(self.star_returns) == 4 else ret
        self.star_last_prediction = next_return

        next_price = round(star_mid + next_return)
        self.star_last_price = star_mid

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
        
        return star_orders
    
    def amethysts_strategy(self, state: TradingState):
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

        return ameth_orders
    
    def orchids_strategy(self, state: TradingState):
        conversion_observations = state.observations.conversionObservations

        south_bid = conversion_observations[ORCHIDS].bidPrice if ORCHIDS in conversion_observations else None
        south_ask = conversion_observations[ORCHIDS].askPrice if ORCHIDS in conversion_observations else None
        transportFees = conversion_observations[ORCHIDS].transportFees if ORCHIDS in conversion_observations else 0
        exportTariff = conversion_observations[ORCHIDS].exportTariff if ORCHIDS in conversion_observations else 0
        importTariff = conversion_observations[ORCHIDS].importTariff if ORCHIDS in conversion_observations else 0
        sunlight = conversion_observations[ORCHIDS].sunlight if ORCHIDS in conversion_observations else None
        humidity = conversion_observations[ORCHIDS].humidity if ORCHIDS in conversion_observations else None

        orchid_position = state.position.get(ORCHIDS, 0)
        max_buy_vol = position_limits[ORCHIDS] - orchid_position
        max_sell_vol = -position_limits[ORCHIDS] - orchid_position

        orchid_bids = state.order_depths[ORCHIDS].buy_orders if state.order_depths[ORCHIDS].buy_orders else None
        orchid_asks = state.order_depths[ORCHIDS].sell_orders if state.order_depths[ORCHIDS].sell_orders else None

        best_orchid_bid = list(orchid_bids.keys())[0]
        best_orchid_ask = list(orchid_asks.keys())[0]

        orchid_mid = best_orchid_bid + (best_orchid_ask - best_orchid_bid) / 2

        print(f"South Bid: {south_bid}")
        print(f"South Ask: {south_ask}")
        print(f"Local Bid: {best_orchid_bid}")
        print(f"Local Ask: {best_orchid_ask}")
        print(f"Import Tariff: {importTariff}")
        print(f"Export Tariff: {exportTariff}")
        print(f"Transport Fees: {transportFees}")

        orchid_orders = []
        conversions = 0

        adjusted_south_bid = south_bid + exportTariff + transportFees
        adjusted_south_ask = south_ask + importTariff + transportFees

        last_price = self.orchid_last_price if self.orchid_last_price else orchid_mid        
        prediction = self.predict_orchid_price(last_price, sunlight, humidity)
        self.orchid_last_price = orchid_mid

        if prediction > best_orchid_ask + 1:
            if adjusted_south_ask < best_orchid_ask:
                if orchid_position < 0:
                    conversions -= orchid_position
                    orchid_orders.append(Order(ORCHIDS, best_orchid_bid, orchid_position))
                else:
                    orchid_orders.append(Order(ORCHIDS, best_orchid_ask, max_buy_vol))
        if prediction < best_orchid_bid:
            if adjusted_south_bid > best_orchid_bid:
                if orchid_position > 0:
                    conversions -= orchid_position
                    orchid_orders.append(Order(ORCHIDS, best_orchid_ask, orchid_position)) 
                else:
                    orchid_orders.append(Order(ORCHIDS, best_orchid_bid, max_sell_vol)) 

        return [], 0
    
    def baskets_strategy(self, state: TradingState):
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

        return result
    