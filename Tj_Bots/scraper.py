import asyncio, os, tempfile, traceback
from pyrogram import Client, filters, enums
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from config import ADMINS, LOG_CHANNEL
from database import db
from Tj_Bots.auto_channels import forward_file_to_channel
from session_manager import active_userbots

SOURCE_BOT = "searchgram_bbot"
SCRAPE_STATUS = {"running": False, "queue": [], "done": 0, "failed": 0, "current": ""}

@Client.on_message(filters.command("add") & filters.user(ADMINS))
async def add_manual(client, message: Message):
    if len(message.command) < 2:
        return await message.reply("⚠️ שימוש: /add שם הסרט\nדוגמה: /add פאודה", quote=True)
    if not active_userbots:
        return await message.reply("❌ אין סשנים פעילים.", quote=True)
    title = " ".join(message.command[1:])
    if SCRAPE_STATUS["running"]:
        SCRAPE_STATUS["queue"].append(title)
        return await message.reply(f"✅ <b>{title}</b> נוסף לתור\n📋 מיקום: <code>{len(SCRAPE_STATUS['queue'])}</code>", parse_mode=enums.ParseMode.HTML, quote=True)
    SCRAPE_STATUS["queue"] = [title]
    SCRAPE_STATUS["done"] = 0
    SCRAPE_STATUS["failed"] = 0
    SCRAPE_STATUS["current"] = ""
    markup = InlineKeyboardMarkup([[InlineKeyboardButton("▶️ התחל", callback_data="scrape_start"), InlineKeyboardButton("❌ ביטול", callback_data="scrape_cancel")]])
    await message.reply(f"🎬 <b>סריקה עבור:</b> <code>{title}</code>\n\nלחץ התחל:", reply_markup=markup, parse_mode=enums.ParseMode.HTML, quote=True)

@Client.on_message(filters.command("addlist") & filters.user(ADMINS))
async def add_list_manual(client, message: Message):
    text = message.text
    lines = text.split("\n")[1:]
    titles = [l.strip() for l in lines if l.strip()]
    if not titles:
        return await message.reply("⚠️ שימוש:\n/addlist\nפאודה\nשכונות הפשע", quote=True)
    if not active_userbots:
        return await message.reply("❌ אין סשנים פעילים.", quote=True)
    if SCRAPE_STATUS["running"]:
        SCRAPE_STATUS["queue"].extend(titles)
        return await message.reply(f"✅ <b>{len(titles)} שמות נוספו לתור</b>\n📋 סה'כ: <code>{len(SCRAPE_STATUS['queue'])}</code>", parse_mode=enums.ParseMode.HTML, quote=True)
    SCRAPE_STATUS["queue"] = titles
    SCRAPE_STATUS["done"] = 0
    SCRAPE_STATUS["failed"] = 0
    markup = InlineKeyboardMarkup([[InlineKeyboardButton("▶️ התחל סריקה", callback_data="scrape_start"), InlineKeyboardButton("❌ ביטול", callback_data="scrape_cancel")]])
    preview = "\n".join(f"• {t}" for t in titles[:5])
    if len(titles) > 5: preview += f"\n... ועוד {len(titles)-5}"
    await message.reply(f"📋 <b>{len(titles)} שמות:</b>\n\n{preview}\n\nלחץ התחל:", reply_markup=markup, parse_mode=enums.ParseMode.HTML, quote=True)

@Client.on_message(filters.command("stopscrape") & filters.user(ADMINS))
async def stop_scrape(client, message: Message):
    SCRAPE_STATUS["running"] = False
    await message.reply("🛑 הסריקה נעצרת.", quote=True)

@Client.on_message(filters.command("scrapestatus") & filters.user(ADMINS))
async def scrape_status(client, message: Message):
    s = SCRAPE_STATUS
    status = "🟢 רצה" if s["running"] else "🔴 עצר"
    await message.reply(f"📊 <b>מצב סריקה</b>\n\nסטטוס: {status}\n⏳ בתור: <code>{len(s['queue'])}</code>\n✅ הושלמו: <code>{s['done']}</code>\n❌ נכשלו: <code>{s['failed']}</code>\n🔄 כרגע: <code>{s['current'] or '—'}</code>", parse_mode=enums.ParseMode.HTML, quote=True)

@Client.on_callback_query(filters.regex("^scrape_") & filters.user(ADMINS))
async def scrape_controls(client, query: CallbackQuery):
    if query.data == "scrape_start":
        if not SCRAPE_STATUS["queue"]:
            return await query.answer("אין תור.", show_alert=True)
        SCRAPE_STATUS["running"] = True
        await query.message.edit(f"🔄 <b>סריקה התחילה!</b>\n📋 בתור: <code>{len(SCRAPE_STATUS['queue'])}</code>\nשלח /scrapestatus לבדיקת מצב", parse_mode=enums.ParseMode.HTML)
        asyncio.create_task(run_scraper(client, query.message))
    elif query.data == "scrape_cancel":
        SCRAPE_STATUS["running"] = False
        SCRAPE_STATUS["queue"] = []
        await query.message.edit("❌ הסריקה בוטלה.")

async def run_scraper(client, status_msg):
    userbot = active_userbots[0]
    while SCRAPE_STATUS["queue"] and SCRAPE_STATUS["running"]:
        title = SCRAPE_STATUS["queue"].pop(0)
        SCRAPE_STATUS["current"] = title
        try:
            count = await scrape_title(client, userbot, title)
            SCRAPE_STATUS["done"] += 1
            await client.send_message(LOG_CHANNEL,
                f"<b>╔════❰ <i>#ScrapeItem</i> ❱════❍</b>\n<b>║╭━━━━━━━━━━━━━━━➣</b>\n<b>║┣⪼ 🎬 כותרת:</b> {title}\n<b>║┣⪼ ✅ נמשכו:</b> <code>{count}</code>\n<b>║┣⪼ 📋 נותרו:</b> <code>{len(SCRAPE_STATUS['queue'])}</code>\n<b>║╰━━━━━━━━━━━━━━━➣</b>\n<b>╚═════════════════❍</b>",
                parse_mode=enums.ParseMode.HTML)
        except Exception as e:
            SCRAPE_STATUS["failed"] += 1
            print(f"[Scraper] שגיאה ב-{title}: {e}")
            traceback.print_exc()
        await asyncio.sleep(30)
    SCRAPE_STATUS["running"] = False
    SCRAPE_STATUS["current"] = ""
    await client.send_message(LOG_CHANNEL,
        f"<b>╔════❰ <i>#ScrapeComplete</i> ❱════❍</b>\n<b>║╭━━━━━━━━━━━━━━━➣</b>\n<b>║┣⪼ ✅ הושלמו:</b> <code>{SCRAPE_STATUS['done']}</code>\n<b>║┣⪼ ❌ נכשלו:</b> <code>{SCRAPE_STATUS['failed']}</code>\n<b>║╰━━━━━━━━━━━━━━━➣</b>\n<b>╚═════════════════❍</b>",
        parse_mode=enums.ParseMode.HTML)

async def scrape_title(client, userbot, title):
    pulled = 0
    page = 1
    while True:
        await userbot.send_message(SOURCE_BOT, title)
        await asyncio.sleep(5)

        bot_msg = None
        async for msg in userbot.get_chat_history(SOURCE_BOT, limit=5):
            if msg.reply_markup:
                bot_msg = msg
                break

        if not bot_msg or not bot_msg.reply_markup:
            print(f"[Scraper] אין reply_markup עבור {title}")
            break

        print(f"[Scraper] reply_markup type: {type(bot_msg.reply_markup)}")
        print(f"[Scraper] reply_markup: {bot_msg.reply_markup}")

        buttons = _extract_buttons(bot_msg.reply_markup)
        print(f"[Scraper] נמצאו {len(buttons)} כפתורים")

        if not buttons:
            break

        for btn in buttons:
            btn_data = _get_btn_data(btn)
            if not btn_data:
                continue
            if btn_data in ("noop",) or btn_data.startswith("search#"):
                continue
            try:
                btn_text = btn.text if hasattr(btn, 'text') and btn.text else btn_data
                print(f"[Scraper] לוחץ על: {btn_text}")
                await bot_msg.click(btn_text, quote=True)
                await asyncio.sleep(3)

                video_msg = None
                async for msg in userbot.get_chat_history(SOURCE_BOT, limit=3):
                    if msg.video:
                        video_msg = msg
                        break

                if video_msg:
                    print(f"[Scraper] נמצא וידאו!")
                    await _save_and_forward(client, video_msg)
                    pulled += 1
                    await asyncio.sleep(5)
                else:
                    print(f"[Scraper] לא נמצא וידאו")
            except Exception as e:
                print(f"[Scraper] שגיאה בכפתור: {e}")
                traceback.print_exc()
                continue

        next_btn = _find_next_page(bot_msg.reply_markup, page)
        if not next_btn:
            break
        next_text = next_btn.text if hasattr(next_btn, 'text') and next_btn.text else _get_btn_data(next_btn)
        await bot_msg.click(next_text, quote=True)
        await asyncio.sleep(3)
        page += 1

    return pulled

async def _save_and_forward(client, video_msg):
    media = video_msg.video
    caption = video_msg.caption or ""
    file_data = {
        'file_unique_id': media.file_unique_id,
        'file_id': media.file_id,
        'file_name': getattr(media, 'file_name', None) or caption or f"Video {video_msg.id}",
        'file_size': media.file_size,
        'chat_id': video_msg.chat.id,
        'message_id': video_msg.id,
        'caption': caption,
    }
    res = await db.save_file(file_data)
    if res == "saved":
        await forward_file_to_channel(client, db, file_data)

def _get_btn_data(btn):
    if hasattr(btn, 'callback_data') and btn.callback_data:
        return btn.callback_data
    if hasattr(btn, 'text') and btn.text:
        return btn.text
    return None

def _extract_buttons(reply_markup):
    buttons = []
    if not reply_markup:
        return buttons
    if hasattr(reply_markup, 'inline_keyboard'):
        for row in reply_markup.inline_keyboard:
            for btn in row:
                buttons.append(btn)
    elif hasattr(reply_markup, 'keyboard'):
        for row in reply_markup.keyboard:
            for btn in row:
                buttons.append(btn)
    return buttons

def _find_next_page(reply_markup, current_page):
    for btn in _extract_buttons(reply_markup):
        data = _get_btn_data(btn)
        if data and f"#{current_page+1}" in data:
            return btn
    return None
    
