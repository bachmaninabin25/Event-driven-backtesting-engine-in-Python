class Event:
    pass


class MarketEvent(Event):
    def __init__(self):
        self.type = "MARKET"


class SignalEvent(Event):
    def __init__(self, symbol, signal_type, strength=1.0):
        self.type = "SIGNAL"
        self.symbol = symbol
        self.signal_type = signal_type  # 'LONG', 'SHORT', 'EXIT'
        self.strength = strength


class OrderEvent(Event):
    def __init__(self, symbol, order_type, quantity, direction):
        self.type = "ORDER"
        self.symbol = symbol
        self.order_type = order_type  # 'MKT' or 'LMT'
        self.quantity = quantity
        self.direction = direction  # 'BUY' or 'SELL'

    def __repr__(self):
        return f"Order: {self.direction} {self.quantity} {self.symbol} @ {self.order_type}"


class FillEvent(Event):
    def __init__(self, symbol, quantity, direction, fill_cost, commission=0.0):
        self.type = "FILL"
        self.symbol = symbol
        self.quantity = quantity
        self.direction = direction
        self.fill_cost = fill_cost
        self.commission = commission
