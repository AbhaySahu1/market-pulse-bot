from __future__ import annotations

import logging

from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

from market_pulse_bot import handlers
from market_pulse_bot.config import BOT_TOKEN


def main() -> None:
    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        level=logging.INFO,
    )
    if not BOT_TOKEN:
        raise SystemExit("TELEGRAM_BOT_TOKEN is missing. Add it to .env")
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", handlers.start))
    app.add_handler(CommandHandler("help", handlers.help_cmd))
    app.add_handler(CommandHandler("ohlc", handlers.ohlc_cmd))
    app.add_handler(CommandHandler("chart", handlers.chart_cmd))
    app.add_handler(CommandHandler("quote", handlers.quote_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.text_message))
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
