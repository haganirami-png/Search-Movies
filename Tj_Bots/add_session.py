import asyncio
from pyrogram import Client, filters, enums
from pyrogram.types import Message
from pyrogram.errors import SessionPasswordNeeded, PhoneCodeInvalid, PhoneCodeExpired
from config import ADMINS, API_ID, API_HASH
from session_manager import active_userbots
from database import db

pending_sessions = {}

@Client.on_message(filters.command(["cancel"]) & filters.user(ADMINS) & filters.private)
async def cancel_cmd(client, message: Message):
    user_id = message.from_user.id
    if user_id in pending_sessions:
        del pending_sessions[user_id]
        await message.reply("❌ הפעולה בוטלה.", quote=True)
    else:
        await message.reply("אין פעולה פעילה.", quote=True)

@Client.on_message(filters.command("addsession") & filters.user(ADMINS) & filters.private)
async def add_session_cmd(client, message: Message):
    user_id = message.from_user.id
    if user_id in pending_sessions:
        del pending_sessions[user_id]
    await message.reply(
        "📱 <b>הוספת סשן חדש</b>\n\nשלח את מספר הטלפון בפורמט:\n<code>+972501234567</code>\n\nלביטול: /cancel",
        parse_mode=enums.ParseMode.HTML,
        quote=True
    )
    pending_sessions[user_id] = {'step': 'phone'}

@Client.on_message(filters.private & filters.user(ADMINS) & filters.text & ~filters.command([]))
async def session_conversation(client, message: Message):
    user_id = message.from_user.id
    if user_id not in pending_sessions:
        return

    state = pending_sessions[user_id]
    step = state.get('step')

    if step == 'phone':
        phone = message.text.strip()
        if not phone.startswith('+'):
            return await message.reply("❌ פורמט לא תקין. שלח כמו: +972501234567\n\nלביטול: /cancel")
        status = await message.reply("⏳ שולח קוד...")
        try:
            temp_client = Client(name=f"temp_{user_id}", api_id=API_ID, api_hash=API_HASH, in_memory=True)
            await temp_client.connect()
            sent = await temp_client.send_code(phone)
            state['client'] = temp_client
            state['phone'] = phone
            state['phone_code_hash'] = sent.phone_code_hash
            state['step'] = 'code'
            pending_sessions[user_id] = state
            await status.edit("✅ קוד נשלח לטלפון!\n\nשלח את הקוד שקיבלת:\nלביטול: /cancel")
        except Exception as e:
            await status.edit(f"❌ שגיאה: {e}")
            del pending_sessions[user_id]

    elif step == 'code':
        code = message.text.strip().replace(" ", "")
        temp_client = state['client']
        phone = state['phone']
        phone_code_hash = state['phone_code_hash']
        status = await message.reply("⏳ מאמת קוד...")
        try:
            await temp_client.sign_in(phone, phone_code_hash, code)
            session_str = await temp_client.export_session_string()
            me = await temp_client.get_me()
            await temp_client.disconnect()
            new_client = Client(name=f"userbot_{phone.replace('+','')}", api_id=API_ID, api_hash=API_HASH, session_string=session_str, in_memory=True)
            await new_client.start()
            active_userbots.append(new_client)
            await db.ensure_db_channel()
            del pending_sessions[user_id]
            await status.edit(f"✅ <b>סשן נוסף בהצלחה!</b>\n\n👤 שם: {me.first_name}\n📞 טלפון: {phone}\n📡 סשנים פעילים: {len(active_userbots)}", parse_mode=enums.ParseMode.HTML)
        except SessionPasswordNeeded:
            state['step'] = 'password'
            pending_sessions[user_id] = state
            await status.edit("🔐 החשבון מוגן בסיסמה דו-שלבית.\n\nשלח את הסיסמה:\nלביטול: /cancel")
        except (PhoneCodeInvalid, PhoneCodeExpired):
            del pending_sessions[user_id]
            await status.edit("❌ קוד שגוי או פג תוקף. נסה שוב עם /addsession")
        except Exception as e:
            del pending_sessions[user_id]
            await status.edit(f"❌ שגיאה: {e}")

    elif step == 'password':
        password = message.text.strip()
        temp_client = state['client']
        phone = state['phone']
        status = await message.reply("⏳ מאמת סיסמה...")
        try:
            await temp_client.check_password(password)
            session_str = await temp_client.export_session_string()
            me = await temp_client.get_me()
            await temp_client.disconnect()
            new_client = Client(name=f"userbot_{phone.replace('+','')}", api_id=API_ID, api_hash=API_HASH, session_string=session_str, in_memory=True)
            await new_client.start()
            active_userbots.append(new_client)
            await db.ensure_db_channel()
            del pending_sessions[user_id]
            await status.edit(f"✅ <b>סשן נוסף בהצלחה!</b>\n\n👤 שם: {me.first_name}\n📞 טלפון: {phone}\n📡 סשנים פעילים: {len(active_userbots)}", parse_mode=enums.ParseMode.HTML)
        except Exception as e:
            del pending_sessions[user_id]
            await status.edit(f"❌ שגיאה: {e}")
