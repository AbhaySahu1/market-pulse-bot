from __future__ import annotations

import time

import pandas as pd
import yfinance as yf

ALIASES: dict[str, str] = {
    "NIFTY": "^NSEI", "NIFTY50": "^NSEI", "BANKNIFTY": "^NSEBANK", "SENSEX": "^BSESN",
    "SPX": "^GSPC", "SP500": "^GSPC", "NASDAQ": "^IXIC", "DOW": "^DJI",
    "GOLD": "GC=F", "SILVER": "SI=F", "CRUDE": "CL=F", "OIL": "CL=F",
    "BTC": "BTC-USD", "BITCOIN": "BTC-USD", "ETH": "ETH-USD",
    "USDINR": "INR=X", "EURUSD": "EURUSD=X",
}
PERIODS: set[str] = {"1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"}
INTERVALS: set[str] = {"1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo"}
INTRADAY_INTERVALS: set[str] = {"1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h"}
INTERVAL_MAX_PERIOD: dict[str, str] = {"1m": "5d", "2m": "1mo", "5m": "1mo", "15m": "1mo", "30m": "1mo", "90m": "1mo", "60m": "1y", "1h": "1y"}
_PERIOD_ORDER: list[str] = ["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"]
_CACHE_TTL = 45.0
_CACHE: dict[tuple[str, str, str], tuple[float, pd.DataFrame]] = {}


def clamp_period(period: str, interval: str) -> tuple[str, bool]:
    limit = INTERVAL_MAX_PERIOD.get(interval)
    if limit is None:
        return period, False
    if period not in _PERIOD_ORDER:
        return limit, True
    if _PERIOD_ORDER.index(period) > _PERIOD_ORDER.index(limit):
        return limit, True
    return period, False


def fetch_history(symbol: str, period: str = "1mo", interval: str = "1d", ttl: float = _CACHE_TTL) -> pd.DataFrame:
    key = (symbol, period, interval)
    cached = _CACHE.get(key)
    if cached is not None:
        age = time.time() - cached[0]
        valid_for = ttl if not cached[1].empty else 15.0
        if age < valid_for:
            return cached[1].copy()
    df = yf.Ticker(symbol).history(period=period, interval=interval, auto_adjust=False)
    if df is None:
        df = pd.DataFrame()
    if "Close" in df.columns:
        df = df.dropna(subset=["Close"])
    _CACHE[key] = (time.time(), df.copy())
    return df.copy()


def resolve_symbol(raw: str) -> str | None:
    symbol = raw.strip().lstrip("$").upper()
    if not symbol:
        return None
    symbol = ALIASES.get(symbol, symbol)
    if any(ch in symbol for ch in ".-=^&"):
        candidates = [symbol]
    else:
        candidates = [symbol, f"{symbol}.NS", f"{symbol}.BO"]
    for candidate in candidates:
        try:
            if not fetch_history(candidate, "5d", "1d", ttl=600).empty:
                return candidate
        except Exception:
            continue
    return None


_LAST_PERIOD_FOR_INTERVAL = {
    "1m": "1d",
    "2m": "1d",
    "5m": "5d",
    "15m": "5d",
    "30m": "5d",
    "60m": "1mo",
    "90m": "1mo",
    "1h": "1mo",
    "1d": "1mo",
    "5d": "3mo",
    "1wk": "1y",
    "1mo": "2y",
}
_CANDLE_INTERVAL_FOR_PERIOD = {
    "1d": "1d",
    "5d": "1d",
    "1mo": "1d",
    "3mo": "1d",
    "6mo": "1d",
    "1y": "1d",
    "2y": "1wk",
    "5y": "1wk",
    "10y": "1mo",
    "ytd": "1d",
    "max": "1mo",
}


def candle_interval_for_period(period: str | None) -> str | None:
    if not period:
        return None
    return _CANDLE_INTERVAL_FOR_PERIOD.get(period)


def last_ohlc(symbol: str, interval: str | None = None) -> dict | None:
    if interval:
        attempts: list[tuple[str, str]] = [(interval, _LAST_PERIOD_FOR_INTERVAL.get(interval, "1mo"))]
    else:
        attempts = [("1m", "1d"), ("5m", "5d")]
    df = pd.DataFrame()
    used = ""
    for iv, period in attempts:
        try:
            df = fetch_history(symbol, period, iv, ttl=20)
        except Exception:
            df = pd.DataFrame()
        if not df.empty:
            used = iv
            break
    if df.empty:
        return None
    row = df.iloc[-1]
    try:
        daily = fetch_history(symbol, "1mo", "1d", ttl=300)
    except Exception:
        daily = pd.DataFrame()
    prev_close: float | None = None
    if "Close" in daily.columns and len(daily) >= 2:
        prev_close = float(daily["Close"].iloc[-2])
    volume: float | None = None
    if "Volume" in df.columns and pd.notna(row["Volume"]):
        volume = float(row["Volume"])
    return {
        "symbol": symbol,
        "interval": used,
        "time": df.index[-1],
        "open": float(row["Open"]),
        "high": float(row["High"]),
        "low": float(row["Low"]),
        "close": float(row["Close"]),
        "volume": volume,
        "prev_close": prev_close,
    }


def snapshot(symbol: str) -> dict:
    values: dict = {
        "last": None,
        "prev_close": None,
        "open": None,
        "day_high": None,
        "day_low": None,
        "year_high": None,
        "year_low": None,
        "market_cap": None,
        "currency": None,
        "exchange": None,
    }
    try:
        fast_info = yf.Ticker(symbol).fast_info
    except Exception:
        return values
    sources = {
        "last": "last_price",
        "prev_close": "previous_close",
        "open": "open",
        "day_high": "day_high",
        "day_low": "day_low",
        "year_high": "year_high",
        "year_low": "year_low",
        "market_cap": "market_cap",
        "currency": "currency",
        "exchange": "exchange",
    }
    for key, attr in sources.items():
        try:
            values[key] = getattr(fast_info, attr)
        except Exception:
            values[key] = None
    return values


_SEARCH_CACHE: dict[str, tuple[float, str | None]] = {}
_SKIP_QUOTE_TYPES = {"ARTICLE", "AUDIO", "BLOG", "NEWS", "STORY", "VIDEO"}


def search_symbol(query: str) -> str | None:
    text = " ".join(query.split())
    if not text:
        return None
    key = text.lower()
    cached = _SEARCH_CACHE.get(key)
    if cached is not None:
        age = time.time() - cached[0]
        if age < (600.0 if cached[1] else 60.0):
            return cached[1]
    found: str | None = None
    try:
        for quote in yf.Search(text, max_results=10).quotes:
            symbol = quote.get("symbol")
            quote_type = str(quote.get("quoteType") or "").upper()
            if symbol and quote_type not in _SKIP_QUOTE_TYPES:
                found = str(symbol)
                break
    except Exception:
        found = None
    _SEARCH_CACHE[key] = (time.time(), found)
    return found
