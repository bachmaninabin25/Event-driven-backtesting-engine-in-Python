import pandas as pd
from abc import ABC, abstractmethod
from events import OrderEvent, FillEvent


class Portfolio(ABC):
    @abstractmethod
    def update_timeindex(self, event):
        raise NotImplementedError

    @abstractmethod
    def update_fill(self, event):
        raise NotImplementedError

    @abstractmethod
    def generate_naive_order(self, signal):
        raise NotImplementedError


class NaivePortfolio(Portfolio):
    def __init__(self, bars, events, start_date, initial_capital=100_000.0):
        self.bars = bars
        self.events = events
        self.start_date = start_date
        self.initial_capital = initial_capital

        self.symbol_list = bars.symbol_list

        self.current_positions = {s: 0 for s in self.symbol_list}
        self.current_holdings = self._init_holdings()

        self.all_positions = []
        self.all_holdings = []

    def _init_holdings(self):
        h = {s: 0.0 for s in self.symbol_list}
        h["cash"] = self.initial_capital
        h["commission"] = 0.0
        h["total"] = self.initial_capital
        h["returns"] = 0.0
        h["datetime"] = self.start_date
        return h

    def update_timeindex(self, event):
        # snapshot current market value of each position
        positions = {s: self.current_positions[s] for s in self.symbol_list}
        positions["datetime"] = self.bars.get_latest_bar(self.symbol_list[0])[0]
        self.all_positions.append(positions)

        holdings = {}
        holdings["datetime"] = positions["datetime"]
        holdings["cash"] = self.current_holdings["cash"]
        holdings["commission"] = self.current_holdings["commission"]

        market_value = 0.0
        for s in self.symbol_list:
            price = self.bars.get_latest_bar_value(s, "price")
            mv = self.current_positions[s] * price
            holdings[s] = mv
            market_value += mv

        holdings["total"] = holdings["cash"] + market_value

        prev_total = self.all_holdings[-1]["total"] if self.all_holdings else self.initial_capital
        holdings["returns"] = (holdings["total"] / prev_total) - 1.0

        self.all_holdings.append(holdings)
        self.current_holdings["total"] = holdings["total"]

    def generate_naive_order(self, signal):
        order = None
        symbol = signal.symbol
        sig_type = signal.signal_type
        fixed_qty = 100  # flat position size

        cur_qty = self.current_positions[symbol]

        if sig_type == "LONG" and cur_qty == 0:
            order = OrderEvent(symbol, "MKT", fixed_qty, "BUY")
        elif sig_type == "SHORT" and cur_qty == 0:
            order = OrderEvent(symbol, "MKT", fixed_qty, "SELL")
        elif sig_type == "EXIT":
            if cur_qty > 0:
                order = OrderEvent(symbol, "MKT", abs(cur_qty), "SELL")
            elif cur_qty < 0:
                order = OrderEvent(symbol, "MKT", abs(cur_qty), "BUY")

        if order:
            self.events.put(order)

    def update_fill(self, event):
        if event.type != "FILL":
            return

        symbol = event.symbol
        direction = event.direction
        qty = event.quantity
        cost = event.fill_cost
        commission = event.commission

        if direction == "BUY":
            self.current_positions[symbol] += qty
            self.current_holdings["cash"] -= (cost + commission)
        elif direction == "SELL":
            self.current_positions[symbol] -= qty
            self.current_holdings["cash"] += (cost - commission)

        self.current_holdings["commission"] += commission

    @property
    def equity_curve(self):
        df = pd.DataFrame(self.all_holdings)
        df.set_index("datetime", inplace=True)
        df["equity_curve"] = (1.0 + df["returns"]).cumprod()
        df["drawdown"] = df["equity_curve"] / df["equity_curve"].cummax() - 1.0
        return df
