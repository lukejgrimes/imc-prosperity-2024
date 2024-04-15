from datamodel import TradingState, Order
from collections import deque
import numpy as np

ORCHIDS = "ORCHIDS"

position_limits = {ORCHIDS: 100}

class Trader:
    def __init__(self):
        self.last_price = None

    def run(self, state: TradingState):
        plain_observations = state.observations.plainValueObservations # Dict[Product, Int]
        conversion_observations = state.observations.conversionObservations # Dict[Product, ConversionObservation]

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
        orchid_spread = best_orchid_ask - best_orchid_bid

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


        last_price = self.last_price if self.last_price else orchid_mid        
        prediction = self.predict(last_price, sunlight, humidity)
        self.last_price = orchid_mid

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

        result = {ORCHIDS: orchid_orders}
        traderData = ""

        return result, conversions, traderData
    
    def predict(self, last_price, sunlight, humidity):
        coef = [0.9996717565693496, 1.1443871506246691e-05, 0.0010130090910631384]
        next_price = 0.24488328854047636

        X = np.column_stack([last_price, sunlight, humidity])
        coef = np.reshape(coef, (1, 3))
        next_price = next_price + coef @ X.T

        return next_price
    