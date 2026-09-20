# Market Pulse

A Telegram bot that answers market-data questions using Yahoo Finance. Send a ticker or company name to get the latest OHLC candle, ask for a chart to get a candlestick screenshot, or ask for a quote snapshot. Natural language works too.

Bot handle used by this deployment: `@Marketpulse123_bot`

## Features

- **Latest OHLC candle** - 1-minute candle by default; `last day ohlc` or `yesterday` returns the previous session's daily candle, and other intervals (for example `1h`) are available on request
- **Candlestick screenshots** - dark-themed charts rendered with mplfinance for any range/interval Yahoo supports
- **Quote snapshots** - last, previous close, open, day range, 52-week range, market cap, currency, exchange
- **Natural language** - `chart reliance 5 days`, `one month of tata motors`, `reliance ka chart`
- **Remembers your last ticker** - `last day ohlc` reuses the symbol from your previous query; if none is known yet, the bot asks which ticker instead of dumping help
- **Company names** - `godrej properties` and `tata motors` resolve through Yahoo search when they are not valid tickers
- **Number words** - `one month`, `two weeks`, `five days` work the same as `1 month`, `2 weeks`, `5 days`
- **Ticker resolution** - `RELIANCE` resolves to `RELIANCE.NS`, then `RELIANCE.BO`; aliases for indices, commodities and crypto (`NIFTY` -> `^NSEI`, `GOLD` -> `GC=F`, `BTC` -> `BTC-USD`, ...)
- **Request cache** - TTL caches for history, symbol searches and quotes so repeated queries do not hammer Yahoo Finance
- **Range clamping** - oversized ranges for intraday intervals are trimmed automatically (for example `1y` of 1m data becomes `5d`)

## Requirements

- Python 3.12+ and [uv](https://docs.astral.sh/uv/)
- A Telegram bot token from [@BotFather](https://t.me/BotFather)
- Internet access to Yahoo Finance (no API key required)

## Configuration

Credentials live in `.env` in the project root (git-ignored):

```dotenv
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHANNEL_NAME=-1001234567890
```

`TELEGRAM_CHANNEL_NAME` is optional; it is loaded for channel posting if you extend the bot. `TELEGRAM_CHAT_ID` is accepted as a fallback key name.

## Run

```bash
uv sync
uv run market-pulse-bot
```

The bot long-polls Telegram until stopped with Ctrl+C.

## Usage

Send a ticker or company name for its latest candle:

```
AAPL              -> last 1-minute OHLC candle
RELIANCE          -> RELIANCE.NS, last 1-minute OHLC candle
NIFTY             -> ^NSEI, last 1-minute OHLC candle
godrej properties -> GODREJPROP.NS, last 1-minute OHLC candle
```

Ask follow-up questions and the bot reuses the ticker you last used:

```
godrej properties    -> GODREJPROP.NS candle
last day ohlc data   -> GODREJPROP.NS, previous session daily candle
one month chart      -> GODREJPROP.NS, last month, daily candles
```

More examples:

| Message | Result |
| --- | --- |
| `chart TSLA 5d 1d` | Last 5 days, daily candles |
| `chart BTC-USD 1d 5m` | Last day, 5-minute candles |
| `reliance 3 months` | RELIANCE.NS, last 3 months, daily candles |
| `last day ohlc of godrej properties` | Previous session's daily candle |
| `yesterday ohlc of tata motors` | Same for TATA MOTORS |
| `/ohlc godrej properties` | Latest candle for a company name |
| `/chart MSFT 1mo 1h` | Last month, hourly candles |
| `/quote MSFT` | Quote snapshot |
| `/help` | Command list |

### Ranges and intervals

Yahoo Finance ranges: `1d`, `5d`, `1mo`, `3mo`, `6mo`, `1y`, `2y`, `5y`, `10y`, `ytd`, `max`

Yahoo Finance intervals: `1m`, `2m`, `5m`, `15m`, `30m`, `60m`, `90m`, `1h`, `1d`, `5d`, `1wk`, `1mo`

When a range exceeds what Yahoo serves for an intraday interval, the bot trims it and says so in the chart caption.

## Project layout

```
src/market_pulse_bot/
  bot.py       Telegram application wiring and polling entrypoint
  config.py    .env loading, BOT_TOKEN / CHANNEL_ID
  handlers.py  command and free-text handlers, per-chat symbol memory, formatting
  market.py    Yahoo Finance access: history, symbol resolution, name search, quotes, cache
  charts.py    mplfinance candlestick rendering to PNG
  queries.py   free text to structured query parsing
```

## Development

```bash
uv run python -m py_compile src/market_pulse_bot/*.py
```

## Troubleshooting

- **"Couldn't find market data"** - check the ticker or company name; Indian symbols usually need `.NS` (NSE) or `.BO` (BSE), which the bot appends automatically when a bare symbol fails.
- **Wrong company resolved** - company-name queries use Yahoo's search ranking; be more specific (for example `godrej properties` instead of `godrej`) or send the exact ticker.
- **"Which ticker or company?"** - the query had no symbol and the chat has no remembered ticker yet; send a name once and follow-ups will work.
- **Empty chart or stale prices** - Yahoo may briefly rate-limit or be unavailable; retry in a moment.
- **Bot does not reply** - only one process can poll a token at a time; make sure no other instance is running and check the log for HTTP errors.
- **"Range trimmed ..."** - Yahoo does not serve long intraday histories, so the bot clamps to the maximum allowed.

## Superpowers skills

This repository vendors the [Superpowers](https://github.com/obra/superpowers) skills (v6.4.1) under `.opencode/skills/`, so they are available as OpenCode agent skills while working in this project.
