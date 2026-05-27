import asyncio, time, re
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait
from config import ADMINS
from database import db
from Tj_Bots.auto_channels import forward_file_to_channel
from Tj_Bots.caption_builder import build_caption

INDEX_STATUS = {}

@Client.on_message(filters.command("index") & filters.user(ADMINS))
async def index_handler(client, message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        return await message.reply("⚠️ שימוש:\n`/index [קישור] - [התחלה]`", quote=True)
    full_arg = args[1]
    start_id = 1
    if " - " in full_arg:
        parts = full_arg.split(" - ")
        link = parts[0].strip()
        try: start_id = int(parts[1].strip())
        except: return await message.reply("❌ מספר התחלה לא תקין.", quote=True)
    else:
        link = full_arg.strip()
    regex = r"(?:https?://)?(?:t\.me|telegram\.me)/(?:c/)?([\w\d]+)/(\d+)"
    match = re.match(regex, link)
    if not match: return await message.reply("❌ קישור לא תקין.", quote=True)
    identifier = match.group(1)
    end_id = int(match.group(2))
    chat_id = int(f"-100{identifier}") if identifier.isdigit() else identifier
    try:
        chat = await client.get_chat(chat_id)
        chat_id = chat.id
    except Exception as e:
        return await message.reply(f"❌ לא מצליח לגשת לערוץ.\n{e}", quote=True)
    INDEX_STATUS[chat_id] = True
    stop_btn = InlineKeyboardMarkup([[InlineKeyboardButton("🛑 עצור", callback_data=f"stop_idx_{chat_id}")]])
    status = await message.reply(f"⏳ **מתחיל אינדקס...**\nערוץ: `{chat.title}`\nטווח: `{start_id}` עד `{end_id}`", reply_markup=stop_btn, quote=True)
    total_saved = total_dups = total_channels = 0
    last_update = time.time()
    current_id = start_id
    while current_id <= end_id:
        if not INDEX_STATUS.get(chat_id, False):
            await status.edit("🛑 **האינדקס נעצר.**")
            return
        batch_end = min(current_id + 200, end_id + 1)
        try:
            messages = await client.get_messages(chat_id, list(range(current_id, batch_end)))
        except FloodWait as e:
            await asyncio.sleep(e.value + 1)
            continue
        except:
            current_id += 200
            continue
        for msg in messages:
            if not msg or not msg.media: continue
            if msg.media != enums.MessageMediaType.VIDEO: continue
            media = getattr(msg, 'video', None)
            if not media: continue
            file_name = getattr(media, 'file_name', None) or msg.caption or f"Video {msg.id}"
            data = {'file_unique_id': media.file_unique_id, 'file_id': media.file_id, 'file_name': file_name, 'file_size': media.file_size, 'chat_id': chat_id, 'message_id': msg.id, 'caption': msg.caption or ""}
            res = await db.save_file(data)
            if res == "saved":
                total_saved += 1
                invite = await forward_file_to_channel(client, db, data)
                if invite: total_channels += 1
            else:
                total_dups += 1
        current_id += 200
        if time.time() - last_update >= 5:
            try:
                await status.edit(f"⏳ **שומר...**\n📍 הודעה: `{min(current_id, end_id)}/{end_id}`\n✅ נשמרו: `{total_saved}`\n📡 ערוצים: `{total_channels}`\n♻️ כפולים: `{total_dups}`", reply_markup=stop_btn)
                last_update = time.time()
            except: pass
    INDEX_STATUS[chat_id] = False
    await status.edit(f"✅ **הושלם!**\n📂 נשמרו: `{total_saved}`\n📡 ערוצים: `{total_channels}`\n♻️ כפולים: `{total_dups}`")

@Client.on_callback_query(filters.regex(r"^stop_idx_"))
async def stop_index_callback(client, query):
    try: chat_id = int(query.data.split("_")[-1])
    except: chat_id = query.data.split("_")[-1]
    if chat_id in INDEX_STATUS:
        INDEX_STATUS[chat_id] = False
        await query.answer("🛑 עוצר...", show_alert=True)
        await query.message.edit("🛑 **נעצר.**")
    else:
        await query.answer("הסתיים.", show_alert=True)

@Client.on_message(filters.command("newindex") & filters.user(ADMINS))
async def new_channel_watch(client, message):
    if len(message.command) < 2:
        return await message.reply("ℹ️ `/newindex -100...`", quote=True)
    try:
        chat_id = int(message.command[1])
        await db.add_watched_channel(chat_id)
        await message.reply(f"✅ ערוץ `{chat_id}` נוסף!", quote=True)
    except Exception as e:
        await message.reply(f"❌ {e}", quote=True)

@Client.on_message(filters.channel)
async def live_watcher(client, message):
    watched = await db.get_watched_channels()
    if message.chat.id not in watched or not message.media: return
    if message.media != enums.MessageMediaType.VIDEO: return
    media = getattr(message, 'video', None)
    if not media: return
    file_name = getattr(media, 'file_name', None) or message.caption or f"Video {message.id}"
    data = {'file_unique_id': media.file_unique_id, 'file_id': media.file_id, 'file_name': file_name, 'file_size': media.file_size, 'chat_id': message.chat.id, 'message_id': message.id, 'caption': message.caption or ""}
    res = await db.save_file(data)
    if res == "saved":
        await forward_file_to_channel(client, db, data)
