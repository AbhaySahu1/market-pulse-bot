from __future__ import annotations

import re
from dataclasses import dataclass

RANGES = {"1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"}
INTERVALS = {"1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo"}
CHART_WORDS = {
    "chart",
    "charts",
    "candle",
    "candles",
    "candlestick",
    "candlesticks",
    "graph",
    "plot",
    "screenshot",
    "image",
    "pic",
    "photo",
    "picture",
    "draw",
    "show",
    "see",
    "view",
    "dekho",
    "dikhao",
    "dikha",
}
OHLC_WORDS = {"ohlc", "ohlcv", "price", "latest", "now", "current"}
QUOTE_WORDS = {"quote", "quotes", "info", "stats", "details", "fundamentals", "summary", "snapshot"}
STOPWORDS = {
    "the",
    "for",
    "of",
    "a",
    "an",
    "me",
    "my",
    "send",
    "get",
    "give",
    "please",
    "pls",
    "plz",
    "and",
    "last",
    "past",
    "previous",
    "prev",
    "on",
    "in",
    "at",
    "stock",
    "share",
    "shares",
    "can",
    "you",
    "i",
    "want",
    "need",
    "it",
    "its",
    "is",
    "doing",
    "how",
    "what",
    "whats",
    "today",
    "today's",
    "todays",
    "yesterday",
    "data",
    "hi",
    "hello",
    "hey",
    "yo",
    "thanks",
    "thank",
    "bye",
    "gm",
    "good",
    "morning",
    "evening",
    "ka",
    "ki",
    "ke",
    "kya",
    "hai",
    "hain",
    "batao",
    "bhej",
    "bhejo",
    "mera",
    "mere",
    "mujhe",
    "iska",
    "uska",
    "kitna",
    "abhi",
}
NUMBER_WORDS = {
    "one": "1",
    "two": "2",
    "three": "3",
    "four": "4",
    "five": "5",
    "six": "6",
    "seven": "7",
    "eight": "8",
    "nine": "9",
    "ten": "10",
    "eleven": "11",
    "twelve": "12",
    "thirteen": "13",
    "fourteen": "14",
    "fifteen": "15",
    "sixteen": "16",
    "seventeen": "17",
    "eighteen": "18",
    "nineteen": "19",
    "twenty": "20",
    "thirty": "30",
    "forty": "40",
    "fifty": "50",
    "sixty": "60",
    "seventy": "70",
    "eighty": "80",
    "ninety": "90",
}

_RESERVED = RANGES | INTERVALS | CHART_WORDS | OHLC_WORDS | QUOTE_WORDS | STOPWORDS
_NL_SPAN = re.compile(
    r"(\d+)\s*(min|mins|minute|minutes|hour|hours|hr|hrs|day|days|week|weeks|month|months|year|years|yr|yrs)\b",
    re.IGNORECASE,
)
_SYMBOL = re.compile(r"[A-Z0-9.^=\-]{1,16}")
_SPLIT = re.compile(r"[\s,]+")
_WORD_NUM = re.compile(r"\b(" + "|".join(NUMBER_WORDS) + r")\b", re.IGNORECASE)
_ARTICLE_UNIT = re.compile(r"\b(?:a|an)\s+(min|minute|hour|day|week|month|year)s?\b", re.IGNORECASE)
_LAST_UNIT = re.compile(r"\b(?:last|past|previous|prev)\s+(min|minute|hour|day|week|month|year)s?\b", re.IGNORECASE)
_RELATIVE_DAY = re.compile(r"\b(?:today|yesterday)\b", re.IGNORECASE)
_MINUTE_UNITS = {"min", "mins", "minute", "minutes"}
_HOUR_UNITS = {"hour", "hours", "hr", "hrs"}
_DAY_UNITS = {"day", "days"}
_WEEK_UNITS = {"week", "weeks"}
_MONTH_UNITS = {"month", "months"}
_PERIOD_FOR_INTERVAL = {
    "1m": "1d",
    "2m": "1d",
    "5m": "5d",
    "15m": "5d",
    "30m": "5d",
    "60m": "1mo",
    "90m": "1mo",
    "1h": "1mo",
    "1d": "5d",
    "5d": "1mo",
    "1wk": "1y",
    "1mo": "5y",
}
_INTERVAL_FOR_PERIOD = {
    "1d": "5m",
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


@dataclass(slots=True)
class Query:
    intent: str
    symbol: str | None = None
    period: str | None = None
    interval: str | None = None


def parse(text: str) -> Query | None:
    working = text.strip()
    if not working:
        return None
    working = _RELATIVE_DAY.sub("1 day", working)
    working = _ARTICLE_UNIT.sub(r"1 \1", working)
    working = _LAST_UNIT.sub(r"1 \1", working)
    working = _WORD_NUM.sub(lambda m: NUMBER_WORDS[m.group(1).lower()], working)
    period: str | None = None
    interval: str | None = None
    match = _NL_SPAN.search(working)
    if match is not None:
        n = int(match.group(1))
        unit = match.group(2).lower()
        if unit in _MINUTE_UNITS:
            candidate = f"{n}m"
            interval = candidate if candidate in INTERVALS else "1m"
        elif unit in _HOUR_UNITS:
            interval = "1h"
        elif unit in _DAY_UNITS:
            period = "1d" if n <= 1 else "5d" if n <= 5 else "1mo" if n <= 30 else "3mo"
        elif unit in _WEEK_UNITS:
            period = "5d" if n <= 1 else "1mo" if n <= 4 else "3mo"
        elif unit in _MONTH_UNITS:
            period = "1mo" if n <= 1 else "3mo" if n <= 3 else "6mo" if n <= 6 else "1y" if n <= 12 else "2y"
        else:
            period = "1y" if n <= 1 else "2y" if n <= 2 else "5y" if n <= 5 else "10y" if n <= 10 else "max"
        working = f"{working[: match.start()]} {working[match.end() :]}"
    tokens = [t for t in _SPLIT.split(working) if t]
    lowered = [t.lower() for t in tokens]
    intent: str | None = None
    if any(t in OHLC_WORDS for t in lowered):
        intent = "ohlc"
    elif any(t in CHART_WORDS for t in lowered):
        intent = "chart"
    elif any(t in QUOTE_WORDS for t in lowered):
        intent = "quote"
    for tok in lowered:
        if tok in RANGES:
            if period is None:
                period = tok
        elif tok in INTERVALS and interval is None:
            interval = tok
    if intent is None and (period is not None or interval is not None):
        intent = "chart"
    symbol_tokens: list[str] = []
    for t in tokens:
        u = t.strip("$").upper()
        u = u.removesuffix("'S").removesuffix("’S")
        if u.lower() in _RESERVED:
            continue
        if _SYMBOL.fullmatch(u) is not None and any(c.isalpha() for c in u):
            symbol_tokens.append(u)
            if len(symbol_tokens) == 4:
                break
    symbol: str | None = " ".join(symbol_tokens) if symbol_tokens else None
    if symbol is None and intent is None and period is None and interval is None:
        return None
    if intent is None:
        intent = "ohlc"
    if intent == "chart":
        if period is None and interval is None:
            period, interval = "5d", "1d"
        elif interval is not None and period is None:
            period = _PERIOD_FOR_INTERVAL[interval]
        elif period is not None and interval is None:
            interval = _INTERVAL_FOR_PERIOD[period]
    return Query(intent, symbol, period, interval)
