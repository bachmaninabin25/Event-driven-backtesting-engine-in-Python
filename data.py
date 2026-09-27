import os
import pandas as pd
from abc import ABC, abstractmethod
from events import MarketEvent


class DataHandler(ABC):
    @abstractmethod
    def get_latest_bar(self, symbol):
        raise NotImplementedError

    @abstractmethod
    def get_latest_bars(self, symbol, N=1):
        raise NotImplementedError

    @abstractmethod
    def get_latest_bar_value(self, symbol, val_type):
        raise NotImplementedError

    @abstractmethod
    def update_bars(self):
        raise NotImplementedError


class HistoricCSVDataHandler(DataHandler):
    def __init__(self, events, csv_dir, symbol_list):
        self.events = events
        self.csv_dir = csv_dir
        self.symbol_list = symbol_list

        self.symbol_data = {}
        self.latest_symbol_data = {s: [] for s in symbol_list}
        self.continue_backtest = True

        self._load_csv_files()

    def _load_csv_files(self):
        combined_index = None

        for symbol in self.symbol_list:
            path = os.path.join(self.csv_dir, f"{symbol}.csv")
            df = pd.read_csv(path, header=0, index_col=0, parse_dates=True)
            df.sort_index(inplace=True)

            # normalize column names
            df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

            # prefer adj_close, fall back to close
            if "adj_close" in df.columns:
                df["price"] = df["adj_close"]
            elif "close" in df.columns:
                df["price"] = df["close"]
            else:
                raise ValueError(f"No close/adj_close column found in {symbol}.csv")

            self.symbol_data[symbol] = df

            if combined_index is None:
                combined_index = df.index
            else:
                combined_index = combined_index.union(df.index)

        # reindex all to same dates and convert to iterators
        for symbol in self.symbol_list:
            self.symbol_data[symbol] = (
                self.symbol_data[symbol]
                .reindex(index=combined_index, method="pad")
                .iterrows()
            )

    def _get_new_bar(self, symbol):
        for row in self.symbol_data[symbol]:
            yield row

    def get_latest_bar(self, symbol):
        bars = self.latest_symbol_data[symbol]
        if not bars:
            raise ValueError(f"No bars available for {symbol}")
        return bars[-1]

    def get_latest_bars(self, symbol, N=1):
        return self.latest_symbol_data[symbol][-N:]

    def get_latest_bar_value(self, symbol, val_type):
        bar = self.get_latest_bar(symbol)
        return getattr(bar[1], val_type)

    def update_bars(self):
        for symbol in self.symbol_list:
            try:
                bar = next(self._get_new_bar(symbol))
            except StopIteration:
                self.continue_backtest = False
            else:
                if bar is not None:
                    self.latest_symbol_data[symbol].append(bar)

        self.events.put(MarketEvent())
