from __future__ import annotations

import asyncio
import html
import logging

from telegram import Message, Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

from market_pulse_bot import charts, market, queries

logger = logging.getLogger(__name__)

HELP_TEXT = """<b>Market Pulse</b>
Yahoo Finance data, straight to Telegram.

<b>Try</b>
<code>AAPL</code> - latest 1-minute OHLC candle
<code>godrej properties</code> - company names work, not just tickers
<code>last day ohlc of godrej properties</code> - previous session's daily candle
<code>last day ohlc</code> - repeats your last ticker
<code>one month chart of tata motors</code> - word numbers work too
<code>quote MSFT</code> - quote snapshot

<b>Commands</b>
/ohlc SYMBOL - latest candle
/chart SYMBOL [range] [interval] - candlestick screenshot
/quote SYMBOL - quote snapshot
/help - this message"""

_SYMBOLS: dict[int, str] = {}


def _remember(chat_id: int, symbol: str) -> None:
    _SYMBOLS[chat_id] = symbol


def _fmt_num(value: float | None, digits: int = 2) -> str:
    if value is None:
        return "—"
    return f"{value:,.{digits}f}"


def _fmt_volume(value: float | None) -> str:
    if value is None:
        return "—"
    if value >= 1e9:
        return f"{value / 1e9:.1f}B"
    if value >= 1e6:
        return f"{value / 1e6:.1f}M"
    if value >= 1e3:
        return f"{value / 1e3:.1f}K"
    return f"{value:,.0f}"


def _fmt_big(value: float | None) -> str:
    if value is None:
        return "—"
    if value >= 1e12:
        return f"{value / 1e12:.1f}T"
    if value >= 1e9:
        return f"{value / 1e9:.1f}B"
    if value >= 1e6:
        return f"{value / 1e6:.1f}M"
    return f"{value:,.0f}"


def _stamp(ts: object) -> str:
    formatter = getattr(ts, "strftime", None)
    if callable(formatter):
        return formatter("%d %b %Y %H:%M %Z").strip()
    return str(ts)


def _range_text(low: float | None, high: float | None) -> str | None:
    if low is None or high is None:
        return None
    return f"{_fmt_num(low)} – {_fmt_num(high)}"


def _row(label: str, value: str | None) -> str | None:
    if value is None:
        return None
    return f"{label:<11}{value}"


async def _not_found(message: Message, raw: str) -> None:
    await message.reply_text(
        f"Couldn't find market data for \"<code>{html.escape(raw)}</code>\". Check the ticker or try /help.",
        parse_mode="HTML",
    )


async def _resolve(raw: str) -> str | None:
    text = raw.strip()
    if not text:
        return None
    if " " in text:
        found = await asyncio.to_thread(market.search_symbol, text)
        if found is not None:
            return found
    symbol = await asyncio.to_thread(market.resolve_symbol, text)
    if symbol is not None:
        return symbol
    return await asyncio.to_thread(market.search_symbol, text)


async def _dispatch(message: Message, context: ContextTypes.DEFAULT_TYPE, q: queries.Query) -> None:
    raw = q.symbol or _SYMBOLS.get(message.chat_id)
    if raw is None:
        await message.reply_text(
            "Which ticker or company? Try <code>reliance</code>, <code>AAPL</code>, or <code>godrej properties</code>.",
            parse_mode="HTML",
        )
        return
    if q.intent == "chart":
        await _reply_chart(message, context, raw, q.period or "5d", q.interval or "1d")
    elif q.intent == "quote":
        await _reply_quote(message, context, raw)
    else:
        interval = q.interval or market.candle_interval_for_period(q.period)
        await _reply_ohlc(message, context, raw, interval)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if message is None:
        return
    await message.reply_text(HELP_TEXT, parse_mode="HTML")


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if message is None:
        return
    await message.reply_text(HELP_TEXT, parse_mode="HTML")


async def ohlc_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if message is None:
        return
    args = context.args or []
    if not args:
        await message.reply_text("Usage: /ohlc SYMBOL  e.g. /ohlc AAPL")
        return
    q = queries.parse("ohlc " + " ".join(args))
    if q is None:
        await message.reply_text("Usage: /ohlc SYMBOL  e.g. /ohlc AAPL")
        return
    await _dispatch(message, context, q)


async def chart_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if message is None:
        return
    args = context.args or []
    usage = "Usage: /chart SYMBOL [range] [interval]  e.g. /chart TSLA 5d 1d"
    if not args:
        await message.reply_text(usage)
        return
    q = queries.parse("chart " + " ".join(args))
    if q is None:
        await message.reply_text(usage)
        return
    await _dispatch(message, context, q)


async def quote_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if message is None:
        return
    args = context.args or []
    if not args:
        await message.reply_text("Usage: /quote SYMBOL  e.g. /quote MSFT")
        return
    q = queries.parse("quote " + " ".join(args))
    if q is None:
        await message.reply_text("Usage: /quote SYMBOL  e.g. /quote MSFT")
        return
    await _dispatch(message, context, q)


async def text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if message is None or not message.text:
        return
    q = queries.parse(message.text)
    if q is None:
        await message.reply_text(HELP_TEXT, parse_mode="HTML")
        return
    await _dispatch(message, context, q)


async def _reply_ohlc(message: Message, context: ContextTypes.DEFAULT_TYPE, raw: str, interval: str | None = None) -> None:
    await context.bot.send_chat_action(chat_id=message.chat_id, action=ChatAction.TYPING)
    try:
        symbol = await _resolve(raw)
        if symbol is None:
            await _not_found(message, raw)
            return
        _remember(message.chat_id, symbol)
        data = await asyncio.to_thread(market.last_ohlc, symbol, interval)
        if data is None:
            await _not_found(message, raw)
            return
        close = data.get("close")
        prev_close = data.get("prev_close")
        change_line = ""
        if prev_close is not None and close is not None:
            change = (close - prev_close) / prev_close * 100 if prev_close else 0.0
            change_line = f"\nChange vs prev close: {change:+.2f}%"
        text = (
            f"<b>{html.escape(symbol)}</b> · last {data.get('interval')} candle\n"
            f"{_stamp(data.get('time'))}\n\n"
            f"<pre>Open   {_fmt_num(data.get('open'))}\n"
            f"High   {_fmt_num(data.get('high'))}\n"
            f"Low    {_fmt_num(data.get('low'))}\n"
            f"Close  {_fmt_num(close)}\n"
            f"Volume {_fmt_volume(data.get('volume'))}</pre>"
            f"{change_line}"
        )
        await message.reply_text(text, parse_mode="HTML")
    except Exception:
        logger.exception("OHLC request failed for %r", raw)
        await message.reply_text("Something went wrong fetching data. Try again in a moment.")


async def _reply_chart(
    message: Message,
    context: ContextTypes.DEFAULT_TYPE,
    raw: str,
    period: str,
    interval: str,
) -> None:
    await context.bot.send_chat_action(chat_id=message.chat_id, action=ChatAction.UPLOAD_PHOTO)
    try:
        symbol = await _resolve(raw)
        if symbol is None:
            await _not_found(message, raw)
            return
        _remember(message.chat_id, symbol)
        period, clamped = await asyncio.to_thread(market.clamp_period, period, interval)
        df = await asyncio.to_thread(market.fetch_history, symbol, period, interval)
        if df is None or df.empty:
            await _not_found(message, raw)
            return
        title = f"{symbol} · {interval} candles · {period}"
        buf = await asyncio.to_thread(charts.render_candles, df, title, interval)
        last = float(df["Close"].iloc[-1])
        first = float(df["Open"].iloc[0])
        change = (last - first) / first * 100 if first else 0.0
        high = float(df["High"].max())
        low = float(df["Low"].min())
        caption = (
            f"<b>{html.escape(symbol)}</b> · {interval} candles · {period}\n"
            f"Close {_fmt_num(last)} ({change:+.2f}%)\n"
            f"High {_fmt_num(high)} · Low {_fmt_num(low)}"
        )
        if clamped:
            caption += f"\nRange trimmed to {period} (Yahoo limit for {interval} data)."
        await message.reply_photo(photo=buf, caption=caption, parse_mode="HTML")
    except Exception:
        logger.exception("Chart request failed for %r", raw)
        await message.reply_text("Something went wrong fetching data. Try again in a moment.")


async def _reply_quote(message: Message, context: ContextTypes.DEFAULT_TYPE, raw: str) -> None:
    await context.bot.send_chat_action(chat_id=message.chat_id, action=ChatAction.TYPING)
    try:
        symbol = await _resolve(raw)
        if symbol is None:
            await _not_found(message, raw)
            return
        _remember(message.chat_id, symbol)
        snap = await asyncio.to_thread(market.snapshot, symbol)
        if snap.get("last") is None:
            await _reply_ohlc(message, context, symbol)
            return
        last = snap.get("last")
        prev_close = snap.get("prev_close")
        open_ = snap.get("open")
        market_cap = snap.get("market_cap")
        currency = snap.get("currency")
        exchange = snap.get("exchange")
        rows = [
            _row("Last", _fmt_num(last) if last is not None else None),
            _row("Prev close", _fmt_num(prev_close) if prev_close is not None else None),
            _row("Open", _fmt_num(open_) if open_ is not None else None),
            _row("Day range", _range_text(snap.get("day_low"), snap.get("day_high"))),
            _row("52w range", _range_text(snap.get("year_low"), snap.get("year_high"))),
            _row("Market cap", _fmt_big(market_cap) if market_cap is not None else None),
            _row("Currency", str(currency) if currency is not None else None),
            _row("Exchange", str(exchange) if exchange is not None else None),
        ]
        body = "\n".join(row for row in rows if row is not None)
        await message.reply_text(f"<b>{html.escape(symbol)}</b>\n\n<pre>{body}</pre>", parse_mode="HTML")
    except Exception:
        logger.exception("Quote request failed for %r", raw)
        await message.reply_text("Something went wrong fetching data. Try again in a moment.")
