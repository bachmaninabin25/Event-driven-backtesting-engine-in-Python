import queue
import time
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec


class Backtest:
    def __init__(
        self,
        csv_dir,
        symbol_list,
        initial_capital,
        start_date,
        data_handler_cls,
        execution_handler_cls,
        portfolio_cls,
        strategy_cls,
        slippage_pct=0.0005,
    ):
        self.csv_dir = csv_dir
        self.symbol_list = symbol_list
        self.initial_capital = initial_capital
        self.start_date = start_date

        self.events = queue.Queue()

        # wire up components
        self.data_handler = data_handler_cls(self.events, csv_dir, symbol_list)
        self.strategy = strategy_cls(self.data_handler, self.events, symbol_list)
        self.portfolio = portfolio_cls(self.data_handler, self.events, start_date, initial_capital)
        self.execution_handler = execution_handler_cls(self.events, self.data_handler, slippage_pct)

    def _run_backtest(self):
        print("Running backtest...")
        while True:
            # advance data by one bar
            if self.data_handler.continue_backtest:
                self.data_handler.update_bars()
            else:
                break

            # drain the event queue
            while True:
                try:
                    event = self.events.get(block=False)
                except queue.Empty:
                    break

                if event.type == "MARKET":
                    self.strategy.calculate_signals(event)
                    self.portfolio.update_timeindex(event)

                elif event.type == "SIGNAL":
                    self.portfolio.generate_naive_order(event)

                elif event.type == "ORDER":
                    self.execution_handler.execute_order(event)

                elif event.type == "FILL":
                    self.portfolio.update_fill(event)

    def _output_summary_stats(self):
        curve = self.portfolio.equity_curve
        returns = curve["returns"].dropna()

        total_return = (curve["equity_curve"].iloc[-1] - 1.0) * 100

        if returns.std() != 0:
            sharpe = np.sqrt(252) * returns.mean() / returns.std()
        else:
            sharpe = 0.0

        drawdown = curve["drawdown"]
        max_dd = drawdown.min() * 100

        # max drawdown duration
        is_dd = drawdown < 0
        dd_groups = (is_dd != is_dd.shift()).cumsum()
        dd_lengths = is_dd.groupby(dd_groups).sum()
        max_dd_duration = int(dd_lengths.max()) if len(dd_lengths) else 0

        print("\n" + "=" * 40)
        print("BACKTEST SUMMARY")
        print("=" * 40)
        print(f"Total Return:        {total_return:.2f}%")
        print(f"Sharpe Ratio:        {sharpe:.4f}")
        print(f"Max Drawdown:        {max_dd:.2f}%")
        print(f"Max DD Duration:     {max_dd_duration} bars")
        print("=" * 40)

        return {
            "total_return": total_return,
            "sharpe": sharpe,
            "max_drawdown": max_dd,
            "max_dd_duration": max_dd_duration,
        }

    def _plot_equity_curve(self):
        curve = self.portfolio.equity_curve

        fig = plt.figure(figsize=(14, 8), facecolor="#0d1117")
        gs = gridspec.GridSpec(2, 1, height_ratios=[3, 1], hspace=0.08)

        # --- equity curve ---
        ax1 = fig.add_subplot(gs[0])
        ax1.set_facecolor("#0d1117")
        ax1.plot(
            curve.index,
            curve["equity_curve"],
            color="#58a6ff",
            linewidth=1.4,
            label="Equity Curve",
        )
        ax1.axhline(1.0, color="#444", linewidth=0.8, linestyle="--")
        ax1.set_ylabel("Portfolio Value (normalized)", color="#c9d1d9", fontsize=11)
        ax1.tick_params(colors="#8b949e", labelbottom=False)
        ax1.spines[:].set_color("#30363d")
        ax1.set_title("Event-Driven Backtester — Pairs Strategy", color="#e6edf3", fontsize=13, pad=12)
        ax1.legend(facecolor="#161b22", edgecolor="#30363d", labelcolor="#c9d1d9")

        # --- drawdown ---
        ax2 = fig.add_subplot(gs[1], sharex=ax1)
        ax2.set_facecolor("#0d1117")
        ax2.fill_between(
            curve.index,
            curve["drawdown"] * 100,
            0,
            color="#f85149",
            alpha=0.6,
            label="Drawdown %",
        )
        ax2.set_ylabel("Drawdown (%)", color="#c9d1d9", fontsize=11)
        ax2.tick_params(colors="#8b949e")
        ax2.spines[:].set_color("#30363d")
        ax2.legend(facecolor="#161b22", edgecolor="#30363d", labelcolor="#c9d1d9")

        plt.savefig("equity_curve.png", dpi=150, bbox_inches="tight", facecolor="#0d1117")
        print("\nPlot saved → equity_curve.png")
        plt.show()

    def run(self):
        t0 = time.time()
        self._run_backtest()
        self._output_summary_stats()
        self._plot_equity_curve()
        print(f"\nFinished in {time.time() - t0:.2f}s")
