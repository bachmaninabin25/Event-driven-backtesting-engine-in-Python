"""
main.py — entry point for the event-driven backtester.

Generates synthetic cointegrated price data if real CSVs are not present,
then runs the pairs strategy end to end.
"""

import os
import numpy as np
import pandas as pd
from datetime import datetime

from data import HistoricCSVDataHandler
from strategy import PairsStrategy
from portfolio import NaivePortfolio
from execution import SimulatedExecutionHandler
from backtest import Backtest


CSV_DIR = "./data"
SYMBOL_LIST = ["ASSET_A", "ASSET_B"]
INITIAL_CAPITAL = 100_000.0
START_DATE = datetime(2020, 1, 1)


def generate_synthetic_data(csv_dir, symbols, n_bars=500, seed=42):
    """
    Generate two cointegrated price series and save as CSVs.
    Useful for smoke-testing without needing real market data.
    """
    os.makedirs(csv_dir, exist_ok=True)
    rng = np.random.default_rng(seed)

    dates = pd.date_range(start="2020-01-01", periods=n_bars, freq="B")

    # common factor + independent noise → cointegrated pair
    common = np.cumsum(rng.normal(0, 1, n_bars))
    noise_a = rng.normal(0, 0.5, n_bars)
    noise_b = rng.normal(0, 0.5, n_bars)

    price_a = 100 + common + noise_a
    price_b = 100 + common + noise_b

    for symbol, prices in zip(symbols, [price_a, price_b]):
        df = pd.DataFrame(
            {
                "Date": dates,
                "Open": prices,
                "High": prices * 1.005,
                "Low": prices * 0.995,
                "Close": prices,
                "Volume": rng.integers(100_000, 1_000_000, n_bars),
                "Adj Close": prices,
            }
        )
        df.set_index("Date", inplace=True)
        path = os.path.join(csv_dir, f"{symbol}.csv")
        df.to_csv(path)
        print(f"Generated {path}")


if __name__ == "__main__":
    # generate synthetic data if CSVs don't exist
    for sym in SYMBOL_LIST:
        if not os.path.exists(os.path.join(CSV_DIR, f"{sym}.csv")):
            print("CSVs not found — generating synthetic cointegrated data...")
            generate_synthetic_data(CSV_DIR, SYMBOL_LIST)
            break

    bt = Backtest(
        csv_dir=CSV_DIR,
        symbol_list=SYMBOL_LIST,
        initial_capital=INITIAL_CAPITAL,
        start_date=START_DATE,
        data_handler_cls=HistoricCSVDataHandler,
        execution_handler_cls=SimulatedExecutionHandler,
        portfolio_cls=NaivePortfolio,
        strategy_cls=PairsStrategy,
    )

    bt.run()
