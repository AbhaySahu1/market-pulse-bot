# Build Plan - Market Pulse Telegram Bot

How this application was prepared, in the order it happened.

## 1. Goal

Build a Telegram bot ("Market Pulse") that answers Yahoo Finance queries: latest 1-minute OHLC data, candlestick screenshots such as the last 5 days of daily candles, quote snapshots, and free-form queries. Credentials come from an env file. The toolchain is uv.

## 2. Technology choices

| Choice | Why |
| --- | --- |
| Python 3.12 | Supported by every dependency; pinned by `uv init --python 3.12` |
| uv 0.12.15 | Single tool for interpreter, virtualenv, dependencies, lockfile and running |
| python-telegram-bot 22.8 | Mature async Telegram framework with a simple polling model |
| yfinance 1.7.0 | Yahoo Finance data without an API key |
| mplfinance 0.12.10b0 + matplotlib 3.11.2 | Candlestick rendering, headless via the Agg backend |
| pandas 3.0.6 | Data frames straight from yfinance |

## 3. Scaffolding with uv

```bash
uv init --name market-pulse-bot --python 3.12 .
uv add python-telegram-bot yfinance mplfinance python-dotenv pandas matplotlib
```

This produced a src layout (`src/market_pulse_bot/`), a `market-pulse-bot` console script in `pyproject.toml`, a `.venv`, and `uv.lock`. The credentials env file was copied into the project root and `.env` was added to `.gitignore`.

## 4. Interfaces fixed before coding

Interfaces were specified up front so four agents could write code in parallel without stepping on each other.

| Module | Public surface |
| --- | --- |
| `config.py` | `BOT_TOKEN`, `CHANNEL_ID`, `.env` loading from the project root |
| `market.py` | `fetch_history`, `resolve_symbol`, `last_ohlc`, `snapshot`, `clamp_period`, alias table, TTL cache |
| `charts.py` | `render_candles(df, title, interval) -> BytesIO` |
| `queries.py` | `Query(intent, symbol, period, interval)`, `parse(text) -> Query or None` |
| `handlers.py` / `bot.py` | Command and text handlers, application wiring, polling entrypoint |

## 5. Parallel agent build

Four general-purpose agents ran concurrently, each owning distinct files so there were no write conflicts:

| Agent | Files | Verification it ran |
| --- | --- | --- |
| A | `config.py`, `market.py` | live AAPL/MSFT calls against Yahoo Finance |
| B | `charts.py` | daily and timezone-aware intraday render tests |
| C | `queries.py` | parser matrix |
| D | `handlers.py`, `bot.py` | compile and import checks |

Agent C's verification command was rejected mid-run, but its module had already been written; the parser contract was re-verified against the full 10-case matrix during integration.

Integration glue was done by the orchestrator: fixed the console-script entrypoint to `market_pulse_bot.bot:main`, emptied the scaffold `__init__.py`, and added `.env` to `.gitignore`.

## 6. Verification results

- Imports of all five modules: ok
- Parser: 10/10 cases, including `chart reliance 5 days` -> `(chart, RELIANCE, 5d, 1d)`, `quote msft` -> `(quote, MSFT)`, `hello` -> `None`
- Live data: `RELIANCE` resolved to `RELIANCE.NS`; last 1m candle at `2026-09-18 15:15 +05:30`; `snapshot("MSFT")` returned all 10 keys; `fetch_history("RELIANCE.NS", "5d", "1d")` returned 5 daily rows; `clamp_period("1y", "1m")` returned `("5d", True)`
- Chart: rendered a 49,213-byte PNG from live daily data
- Bot smoke test: `getMe`, `deleteWebhook` and `getUpdates` all HTTP 200, `Application started`, clean shutdown on SIGTERM

## 7. Decisions and trade-offs

- **Default chart is 5d/1d** because the requested example was "screenshot of past 5 days daily candle".
- **Bare symbols try raw -> `.NS` -> `.BO`** in order; worst case three Yahoo calls, but successful resolutions are cached for 10 minutes.
- **OHLC fallback** from 1m to 5m candles when Yahoo has no 1-minute data for the symbol.
- **Cache TTLs**: 45s default, 20s for intraday OHLC, 300s for daily previous-close lookups, 600s for symbol resolution.
- **Intraday range clamping** because Yahoo only serves limited history per intraday interval.
- **HTML parse mode with escaping** for message formatting, and aligned `<pre>` blocks for OHLC and quote tables.
- **Blocking yfinance calls run in `asyncio.to_thread`** so polling stays responsive while a request is in flight.
- **Agg backend** for matplotlib so charts render in a headless process.
- **Superpowers skills vendored** in `.opencode/skills/` because the global OpenCode config directory on this machine is root-owned and not writable.

## 8. Known limitations and possible next steps

- Yahoo Finance rate limits apply and there is no per-chat throttling yet.
- The query parser is rule-based; company names go through Yahoo search and symbol-less queries reuse the chat's last ticker, but some unusual phrasings still resolve imperfectly.
- Charts are rendered per request with no image caching.
- Polling only; a webhook deployment would scale better.
- `TELEGRAM_CHANNEL_NAME` is already loaded in `config.py`, so scheduled channel posts are a natural next feature.

## 9. Post-build fixes

- Company names that are not valid tickers (`godrej properties`) resolve through Yahoo's search endpoint before giving up.
- Word numbers (`one month`, `a week`, `last month`) parse the same as digit forms.
- `last day` / `yesterday` OHLC returns the daily candle instead of the 1-minute candle.
- The bot remembers the last resolved symbol per chat and asks "which ticker?" when a query has none.
