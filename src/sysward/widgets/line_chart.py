"""Reusable line chart widget — plotext for detail screens, Sparkline for compact mode."""

from __future__ import annotations

from typing import Any

from textual.app import ComposeResult
from textual.widgets import Sparkline, Static
from textual.containers import Vertical


class LineChart(Vertical):
    """Line chart with two modes: compact (Sparkline) and full (plotext)."""

    DEFAULT_CSS = """
    LineChart {
        height: auto;
    }
    LineChart.compact {
        height: 3;
    }
    LineChart.full {
        height: 12;
        border: round $panel;
        margin: 0 1;
    }
    """

    def __init__(
        self,
        title: str = "",
        y_label: str = "",
        y_range: tuple[float, float] | None = None,
        compact: bool = False,
        *,
        id: str | None = None,
    ) -> None:
        super().__init__(id=id)
        self._title = title
        self._y_label = y_label
        self._y_range = y_range
        self._compact = compact
        self._series: dict[str, dict] = {}  # name -> {color, data, timestamps}
        if compact:
            self.add_class("compact")
        else:
            self.add_class("full")

    def compose(self) -> ComposeResult:
        if self._compact:
            yield Sparkline([], id="chart-spark")
        else:
            from textual_plotext import PlotextPlot
            yield PlotextPlot(id="chart-plot")

    def update_data(
        self,
        data: list[float],
        timestamps: list[float] | None = None,
        series_name: str = "default",
        color: str | None = None,
    ) -> None:
        """Update chart data for a named series."""
        self._series[series_name] = {
            "data": data,
            "timestamps": timestamps,
            "color": color,
        }
        self._refresh_chart()

    def update_from_ring(
        self,
        timed_data: list[tuple[float, float]],
        series_name: str = "default",
        color: str | None = None,
    ) -> None:
        """Update from RingBuffer.last_n_with_time() output."""
        if not timed_data:
            return
        timestamps = [t for t, _ in timed_data]
        values = [v for _, v in timed_data]
        self.update_data(values, timestamps, series_name, color)

    def _refresh_chart(self) -> None:
        if self._compact:
            self._refresh_sparkline()
        else:
            self._refresh_plotext()

    def _refresh_sparkline(self) -> None:
        """Update compact sparkline with first series data."""
        try:
            spark = self.query_one("#chart-spark", Sparkline)
            first = next(iter(self._series.values()), None)
            if first:
                spark.data = first["data"]
        except Exception:
            pass

    def _refresh_plotext(self) -> None:
        """Update full plotext chart."""
        try:
            from textual_plotext import PlotextPlot
            plot_widget = self.query_one("#chart-plot", PlotextPlot)
            plt = plot_widget.plt
            plt.clear_data()
            plt.clear_figure()

            if self._title:
                plt.title(self._title)
            if self._y_label:
                plt.ylabel(self._y_label)
            if self._y_range:
                plt.ylim(*self._y_range)

            plt.theme("dark")

            for name, series in self._series.items():
                data = series["data"]
                ts = series.get("timestamps")
                if not data:
                    continue

                if ts and len(ts) == len(data):
                    # Convert to relative seconds from now
                    import time
                    now = time.time()
                    x = [t - now for t in ts]
                else:
                    x = list(range(len(data)))

                color = series.get("color") or "cyan"
                label = name if name != "default" else self._title or ""
                plt.plot(x, data, color=color, label=label)

            if len(self._series) > 1:
                plt.legend()

            plot_widget.refresh()
        except Exception:
            pass
