import os, tempfile
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from config import ADMINS
from session_manager import load_sessions_from_zip, active_userbots, health_check, remove_session_by_phone, _get_daily_count, _is_rate_limited, DAILY_LIMIT

def sessions_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 רשימת סשנים", callback_data="sess_list"), InlineKeyboardButton("❤️ בדיקת בריאות", callback_data="sess_health")],
        [InlineKeyboardButton("📊 סטטיסטיקות יום", callback_data="sess_stats"), InlineKeyboardButton("🔄 רענן", callback_data="sess_refresh")],
        [InlineKeyboardButton("❌ סגור", callback_data="sess_close")],
    ])

@Client.on_message(filters.command("sessions") & filters.user(ADMINS))
async def cmd_sessions(client, message: Message):
    await message.reply(f"📡 <b>ניהול סשנים</b>\n\nסשנים פעילים: <code>{len(active_userbots)}</code>\n\nשלח קובץ ZIP להוספת סשנים:", reply_markup=sessions_keyboard(), parse_mode="html", quote=True)

@Client.on_message(filters.document & filters.user(ADMINS) & filters.create(lambda _,__,m: m.document and m.document.file_name and m.document.file_name.endswith(".zip")))
async def handle_sessions_zip(client, message: Message):
    status = await message.reply("⏳ מוריד קובץ...", quote=True)
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        await client.download_media(message, file_name=tmp_path)
        await status.edit("⏳ טוען סשנים...")
        count = await load_sessions_from_zip(tmp_path)
        if count == 0:
            await status.edit("❌ לא נמצאו סשנים תקינים.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ סגור", callback_data="sess_close")]]))
        else:
            await status.edit(f"✅ <b>{count} סשנים נטענו!</b>\n📡 סה'כ פעילים: <code>{len(active_userbots)}</code>", reply_markup=sessions_keyboard(), parse_mode="html")
    except Exception as e:
        await status.edit(f"❌ שגיאה: {e}")
    finally:
        os.unlink(tmp_path)

@Client.on_callback_query(filters.regex("^sess_") & filters.user(ADMINS))
async def sessions_callback(client, query: CallbackQuery):
    action = query.data
    if action == "sess_list":
        if not active_userbots: return await query.answer("אין סשנים.", show_alert=True)
        lines = [f"📋 <b>סשנים ({len(active_userbots)})</b>\n"]
        btns = []
        for i, ub in enumerate(active_userbots, 1):
            try:
                me = await ub.get_me()
                phone = ub.name.replace("userbot_","")
                icon = "⛔" if _is_rate_limited(phone) else "✅"
                lines.append(f"{i}. {icon} <a href='tg://user?id={me.id}'>{me.first_name}</a> | <code>+{phone}</code> | {_get_daily_count(phone)}/{DAILY_LIMIT}")
                btns.append([InlineKeyboardButton(f"🗑 הסר +{phone}", callback_data=f"sess_kick_{phone}")])
            except:
                lines.append(f"{i}. ❌ לא זמין")
        btns.append([InlineKeyboardButton("🔙 חזור", callback_data="sess_refresh")])
        await query.message.edit("\n".join(lines), reply_markup=InlineKeyboardMarkup(btns), parse_mode="html")
    elif action == "sess_health":
        await query.answer("בודק...")
        result = await health_check()
        text = f"❤️ <b>בריאות</b>\n\n✅ פעילים: <code>{len(result['alive'])}</code>\n❌ הוסרו: <code>{result['dead_count']}</code>\n\n"
        for s in result['alive']:
            text += f"• {s['name']} | {'⛔' if s['limited'] else '✅'} | {s['today']}/{DAILY_LIMIT}\n"
        await query.message.edit(text, reply_markup=sessions_keyboard(), parse_mode="html")
    elif action == "sess_stats":
        total = sum(_get_daily_count(ub.name.replace("userbot_","")) for ub in active_userbots)
        available = sum(1 for ub in active_userbots if not _is_rate_limited(ub.name.replace("userbot_","")))
        await query.message.edit(f"📊 <b>סטטיסטיקות</b>\n\n📡 פעילים: <code>{len(active_userbots)}</code>\n✅ זמינים: <code>{available}</code>\n🎬 נוצרו היום: <code>{total}</code>\n⚙️ מגבלה: <code>{DAILY_LIMIT}</code>", reply_markup=sessions_keyboard(), parse_mode="html")
    elif action == "sess_refresh":
        await query.message.edit(f"📡 <b>ניהול סשנים</b>\n\nפעילים: <code>{len(active_userbots)}</code>", reply_markup=sessions_keyboard(), parse_mode="html")
    elif action == "sess_close":
        await query.message.delete()
    elif action.startswith("sess_kick_"):
        phone = action.replace("sess_kick_","")
        removed = await remove_session_by_phone(phone)
        await query.answer(f"✅ הוסר" if removed else "לא נמצא", show_alert=True)
        await query.message.edit(f"📡 <b>ניהול סשנים</b>\n\nפעילים: <code>{len(active_userbots)}</code>", reply_markup=sessions_keyboard(), parse_mode="html")
