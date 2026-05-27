from pyrogram import Client, filters
from pyrogram.types import Message
from database import db
from config import UPDATE_CHANNEL, AUTH_CHANNEL_FORCE, PHOTO_URL
from .utils import get_readable_size

@Client.on_message(filters.command("start"))
async def start_handler(client, message: Message):
    user = message.from_user
    await db.add_user(user.id, user.first_name)

    args = message.text.split()
    if len(args) > 1:
        file_id = args[1]
        file = await db.get_file(file_id)
        if file:
            try:
                await client.copy_message(
                    chat_id=message.chat.id,
                    from_chat_id=file['chat_id'],
                    message_id=file['message_id']
                )
            except Exception as e:
                await message.reply(f"❌ שגיאה בשליחת הקובץ: {e}")
            return

    text = (
        f"👋 שלום {user.first_name}!\n\n"
        f"🔍 **בוט חיפוש סרטים וסדרות**\n\n"
        f"פשוט כתוב שם סרט או סדרה ואני אמצא לך את זה!\n\n"
        f"📺 כל סרט/סדרה נשמר בערוץ פרטי משלו."
    )

    await message.reply(text)
