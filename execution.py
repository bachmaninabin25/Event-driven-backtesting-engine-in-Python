from abc import ABC, abstractmethod
from events import FillEvent


class ExecutionHandler(ABC):
    @abstractmethod
    def execute_order(self, event):
        raise NotImplementedError


class SimulatedExecutionHandler(ExecutionHandler):
    """
    Simulates order fills with slippage and commission.

    Slippage: fixed bps applied to close price.
    Commission: max($1, 0.1% of trade value) — IB-style.
    """

    def __init__(self, events, bars, slippage_pct=0.0005):
        self.events = events
        self.bars = bars
        self.slippage_pct = slippage_pct

    def _calc_commission(self, quantity, fill_price):
        trade_value = quantity * fill_price
        return max(1.0, 0.001 * trade_value)

    def execute_order(self, event):
        if event.type != "ORDER":
            return

        symbol = event.symbol
        direction = event.direction
        quantity = event.quantity

        # get latest close
        close = self.bars.get_latest_bar_value(symbol, "price")

        # apply slippage — buys cost more, sells get less
        if direction == "BUY":
            fill_price = close * (1 + self.slippage_pct)
        else:
            fill_price = close * (1 - self.slippage_pct)

        fill_cost = quantity * fill_price
        commission = self._calc_commission(quantity, fill_price)

        fill = FillEvent(
            symbol=symbol,
            quantity=quantity,
            direction=direction,
            fill_cost=fill_cost,
            commission=commission,
        )
        self.events.put(fill)
