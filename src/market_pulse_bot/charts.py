import io

import pandas as pd
import matplotlib

matplotlib.use("Agg")

import mplfinance as mpf

INTRADAY = {"1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h"}
_OHLCV = ("Open", "High", "Low", "Close", "Volume")
_STYLE: dict[str, object] | None = None


def _get_style() -> dict[str, object]:
    global _STYLE
    if _STYLE is None:
        marketcolors = mpf.make_marketcolors(
            up="#26a69a",
            down="#ef5350",
            edge="inherit",
            wick="inherit",
            volume="in",
        )
        _STYLE = mpf.make_mpf_style(
            marketcolors=marketcolors,
            facecolor="#131722",
            figcolor="#131722",
            gridcolor="#2a2e39",
            gridstyle="--",
            y_on_right=True,
            rc={
                "axes.labelcolor": "#d1d4dc",
                "xtick.color": "#d1d4dc",
                "ytick.color": "#d1d4dc",
                "axes.titlecolor": "#d1d4dc",
                "font.size": 10,
            },
        )
    return _STYLE


def render_candles(df: pd.DataFrame, title: str, interval: str) -> io.BytesIO:
    data = df.copy()
    if isinstance(data.index, pd.DatetimeIndex) and data.index.tz is not None:
        data.index = data.index.tz_localize(None)
    data = data[[column for column in _OHLCV if column in data.columns]]
    has_volume = "Volume" in data.columns and float(data["Volume"].fillna(0).sum()) > 0
    datetime_format = "%d %b %H:%M" if interval in INTRADAY else "%d %b %y"
    plot_kwargs: dict[str, object] = {}
    if len(data) >= 20:
        plot_kwargs["mav"] = (20,)
    buf = io.BytesIO()
    mpf.plot(
        data,
        type="candle",
        style=_get_style(),
        title=title,
        ylabel="Price",
        volume=has_volume,
        datetime_format=datetime_format,
        xrotation=20,
        tight_layout=True,
        figsize=(10, 6),
        savefig=dict(fname=buf, format="png", dpi=150, bbox_inches="tight"),
        **plot_kwargs,
    )
    buf.seek(0)
    return buf
