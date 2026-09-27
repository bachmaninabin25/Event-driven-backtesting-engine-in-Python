import numpy as np
from abc import ABC, abstractmethod
from events import SignalEvent


class Strategy(ABC):
    @abstractmethod
    def calculate_signals(self, event):
        raise NotImplementedError


class PairsStrategy(Strategy):
    """
    Mean-reversion pairs strategy.
    Computes spread z-score between two symbols.
    Entry at |z| > 2.0, exit at |z| < 0.5.
    """

    def __init__(self, bars, events, symbol_list, lookback=30,
                 entry_z=2.0, exit_z=0.5):
        if len(symbol_list) != 2:
            raise ValueError("PairsStrategy requires exactly 2 symbols")

        self.bars = bars
        self.events = events
        self.symbol_list = symbol_list
        self.lookback = lookback
        self.entry_z = entry_z
        self.exit_z = exit_z

        # track current position state: None, 'LONG_SPREAD', 'SHORT_SPREAD'
        self.position = None

    def _get_prices(self, symbol):
        bars = self.bars.get_latest_bars(symbol, N=self.lookback)
        return np.array([b[1]["price"] for b in bars])

    def calculate_signals(self, event):
        if event.type != "MARKET":
            return

        sym_a, sym_b = self.symbol_list

        prices_a = self._get_prices(sym_a)
        prices_b = self._get_prices(sym_b)

        if len(prices_a) < self.lookback or len(prices_b) < self.lookback:
            return  # not enough data yet

        # compute spread and z-score
        spread = prices_a - prices_b
        z = (spread[-1] - spread.mean()) / (spread.std() + 1e-9)

        # ENTRY: spread too wide → short A, long B
        if z > self.entry_z and self.position != "SHORT_SPREAD":
            self._emit(sym_a, "SHORT")
            self._emit(sym_b, "LONG")
            self.position = "SHORT_SPREAD"
            print(f"[SIGNAL] SHORT SPREAD  z={z:.2f}")

        # ENTRY: spread too narrow → long A, short B
        elif z < -self.entry_z and self.position != "LONG_SPREAD":
            self._emit(sym_a, "LONG")
            self._emit(sym_b, "SHORT")
            self.position = "LONG_SPREAD"
            print(f"[SIGNAL] LONG SPREAD   z={z:.2f}")

        # EXIT
        elif abs(z) < self.exit_z and self.position is not None:
            self._emit(sym_a, "EXIT")
            self._emit(sym_b, "EXIT")
            self.position = None
            print(f"[SIGNAL] EXIT          z={z:.2f}")

    def _emit(self, symbol, signal_type):
        self.events.put(SignalEvent(symbol, signal_type, strength=1.0))
