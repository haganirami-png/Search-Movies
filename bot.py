"""
bot.py  —  גרסה סופית
"""

import logging
import asyncio
import os
from pyrogram import Client, idle
from config import API_ID, API_HASH, BOT_TOKEN, LOG_CHANNEL
from database import db
from session_manager import stop_all_sessions, set_bot_ref

logging.basicConfig(
    level=logging.ERROR,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

app = Client(
    "TjBot_Session",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    plugins=dict(root="Tj_Bots")
)

async def start_bot():
    print("🤖 הבוט מתחיל לעבוד...")
    await app.start()
    await db.init_database(app)
    set_bot_ref(app)

    if os.path.exists("restart.txt"):
        try:
            with open("restart.txt", "r") as f:
                content = f.read().split()
                if len(content) == 2:
                    chat_id, msg_id = int(content[0]), int(content[1])
                    await app.edit_message_text(chat_id, msg_id, "הבוט הופעל מחדש ✅")
            os.remove("restart.txt")
        except Exception as e:
            print(f"Error editing restart message: {e}")

    try:
        me = await app.get_me()
        await app.send_message(
            LOG_CHANNEL,
            f"#BotStarted\n✅ <b>הבוט הופעל בהצלחה!</b>\n@{me.username}\n\n"
            f"📡 שלח קובץ ZIP עם סשנים כדי להפעיל יצירת ערוצים אוטומטית."
        )
    except:
        pass

    print("✅ הבוט מחובר!")
    await idle()

    await stop_all_sessions()
    await app.stop()

if __name__ == "__main__":
    app.run(start_bot())
