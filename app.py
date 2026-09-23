import os
import threading
import asyncio
from flask import Flask
from main import bot, dp, init_db

app = Flask(__name__)


@app.route("/")
def home():
    return "Bot is running"


@app.route("/health")
def health():
    return "OK"


def run_bot():
    """Botni alohida oqimda ishga tushirish."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    init_db()
    loop.run_until_complete(bot.delete_webhook(drop_pending_updates=True))
    loop.run_until_complete(dp.start_polling(bot))


if __name__ == "__main__":
    # Botni fon oqimida ishga tushirish
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()

    # Flask serverni Render'dagi PORT da ishga tushirish
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)