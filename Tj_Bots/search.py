from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from database import db
from config import UPDATE_CHANNEL, LOG_CHANNEL, ADMINS
from .utils import get_readable_size, clean_filename
import asyncio

@Client.on_message(filters.text & ~filters.command(["start","index","newindex","settings","broadcast","broadcast_groups","stats","restart","clean","channels","watch","font","share","tts","paste","sessions","listchannels","add","addlist"]))
async def search_handler(client, message):
    query = message.text
    if query.startswith("/"): return
    chat_id = message.chat.id
    if message.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        await db.add_group(chat_id, message.chat.title)
        settings = await db.get_settings(chat_id)
        if settings.get('search_trigger') == 'bang' and not query.startswith('!'): return
        if query.startswith('!'): query = query[1:].strip()
    else:
        settings = await db.get_settings(chat_id)
    if len(query) < 2: return
    results = await db.search_files(query)
    if not results:
        try:
            msg = await message.reply(f"**לא נמצאו תוצאות: `{query}`**", quote=True)
            await asyncio.sleep(2)
            await msg.delete()
        except: pass
        return
    try:
        await send_results_page(client, message, results, 1, query, settings)
    except Exception as e:
        print(f"Error: {e}")

@Client.on_callback_query(filters.regex(r"^dl_"))
async def handle_search_click(client, query: CallbackQuery):
    file_id = query.data.split("_")[1]
    bot_username = client.me.username
    await query.answer(url=f"https://t.me/{bot_username}?start={file_id}")

@Client.on_callback_query(filters.regex(r"^watch_"))
async def handle_watch_click(client, query: CallbackQuery):
    file_id = query.data.split("_",1)[1]
    file = await db.get_file(file_id)
    if not file: return await query.answer("❌ לא נמצא.", show_alert=True)
    from Tj_Bots.caption_builder import parse_caption
    info = parse_caption(file.get('caption',''), file.get('file_name',''))
    title = info.get('title','')
    channel = await db.get_media_channel(title) if title else None
    if not channel or not channel.get('invite_link'):
        return await query.answer("⏳ הערוץ עדיין לא נוצר.", show_alert=True)
    await query.answer(url=channel['invite_link'])

@Client.on_callback_query(filters.regex(r"^report_"))
async def handle_report_click(client, query: CallbackQuery):
    file_id = query.data.split("_",1)[1]
    file = await db.get_file(file_id)
    user = query.from_user
    await query.answer("✅ הדיווח נשלח!", show_alert=True)
    file_name = file.get('file_name','לא ידוע') if file else 'לא ידוע'
    try:
        await client.send_message(LOG_CHANNEL,
            "<b>╔════❰ <i>#BrokenLink</i> ❱════❍</b>\n"
            "<b>║╭━━━━━━━━━━━━━━━➣</b>\n"
            f"<b>║┣⪼ 🎬 קובץ:</b> <code>{file_name}</code>\n"
            f"<b>║┣⪼ 👤 דווח:</b> <a href='tg://user?id={user.id}'>{user.first_name}</a>\n"
            "<b>║╰━━━━━━━━━━━━━━━➣</b>\n"
            "<b>╚═════════════════❍</b>",
            parse_mode=enums.ParseMode.HTML)
    except: pass

@Client.on_callback_query(filters.regex(r"^search#"))
async def search_pagination(client, query):
    try:
        _, q_str, page_str = query.data.split("#")
        page = int(page_str)
        settings = await db.get_settings(query.message.chat.id)
        results = await db.search_files(q_str)
        if not results: return await query.answer("פג תוקף.", show_alert=True)
        await send_results_page(client, query.message, results, page, q_str, settings, is_edit=True)
    except Exception as e:
        print(f"Error pagination: {e}")

async def send_results_page(client, message, results, page, query, settings, is_edit=False):
    per_page = settings.get('results_per_page', 10)
    total = len(results)
    total_pages = (total + per_page - 1) // per_page
    start_idx = (page-1) * per_page
    batch = results[start_idx:start_idx+per_page]
    bot_username = client.me.username or "Bot"
    text = f"<b>🔍 תוצאות חיפוש</b>\n\n"
    text += f"<blockquote><b>📌 שאילתה:</b> <code>{query}</code></blockquote>\n"
    text += f"<blockquote><b>🖥 תוצאות:</b> <code>{total}</code></blockquote>\n\n"
    keyboard = []
    display_mode = settings.get('display_mode', 'inline')
    if display_mode == 'inline':
        for res in batch:
            clean = clean_filename(res['file_name'])
            size = get_readable_size(res['file_size'])
            file_id = str(res.get('_id', res.get('file_unique_id','')))
            keyboard.append([InlineKeyboardButton(f"[{size}] {clean}", callback_data=f"dl_{file_id}")])
            keyboard.append([
                InlineKeyboardButton("📺 לצפייה", callback_data=f"watch_{file_id}"),
                InlineKeyboardButton("🚨 קישור שבור", callback_data=f"report_{file_id}"),
            ])
    else:
        chars = ['א','ב','ג','ד','ה','ו','ז','ח','ט','י']
        for i, res in enumerate(batch):
            prefix = chars[i] if i < len(chars) else str(i+1)
            clean = clean_filename(res['file_name'])
            file_id = str(res.get('_id', res.get('file_unique_id','')))
            link = f"https://t.me/{bot_username}?start={file_id}"
            text += f"🎬 **{prefix}. [{clean}]({link})**\n\n"
            keyboard.append([
                InlineKeyboardButton(f"📺 {prefix}. לצפייה", callback_data=f"watch_{file_id}"),
                InlineKeyboardButton("🚨", callback_data=f"report_{file_id}"),
            ])
    nav = []
    if page > 1: nav.append(InlineKeyboardButton('⬅️', callback_data=f"search#{query}#{page-1}"))
    if page < total_pages: nav.append(InlineKeyboardButton('➡️', callback_data=f"search#{query}#{page+1}"))
    if nav: keyboard.append(nav)
    keyboard.append([InlineKeyboardButton(f"📃 עמוד {page}/{total_pages}", callback_data="noop")])
    markup = InlineKeyboardMarkup(keyboard)
    if is_edit:
        await message.edit_text(text, reply_markup=markup, disable_web_page_preview=True)
    else:
        await message.reply_text(text, reply_markup=markup, disable_web_page_preview=True, quote=True)
