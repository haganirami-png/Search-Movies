import os, json, zipfile, asyncio
from datetime import date
from pyrogram import Client, enums
from pyrogram.errors import FloodWait, AuthKeyUnregistered, UserDeactivated
from config import LOG_CHANNEL

os.makedirs("sessions", exist_ok=True)

active_userbots: list[Client] = []
_bot_ref = None
_daily_counts = {}
DAILY_LIMIT = 50

def set_bot_ref(bot):
    global _bot_ref
    _bot_ref = bot

async def _log(text):
    if _bot_ref:
        try:
            await _bot_ref.send_message(LOG_CHANNEL, text, parse_mode=enums.ParseMode.HTML)
        except: pass

def _get_daily_count(phone):
    entry = _daily_counts.get(phone)
    if not entry or entry['date'] != date.today():
        _daily_counts[phone] = {'date': date.today(), 'count': 0}
        return 0
    return entry['count']

def _increment_count(phone):
    if phone not in _daily_counts or _daily_counts[phone]['date'] != date.today():
        _daily_counts[phone] = {'date': date.today(), 'count': 0}
    _daily_counts[phone]['count'] += 1

def _is_rate_limited(phone):
    return _get_daily_count(phone) >= DAILY_LIMIT

async def load_session_from_json(json_data):
    session_str = json_data.get("session_str")
    phone = str(json_data.get("phone", "unknown"))

    if not session_str:
        return None

    # השתמש ב-app_id/hash מה-JSON, אחרת ברירת מחדל
    app_id = json_data.get("app_id") or 2040
    app_hash = json_data.get("app_hash") or "b18441a1ff607e10a989891a5462e627"

    for ub in active_userbots:
        if ub.name == f"userbot_{phone}": return None
    try:
        client = Client(name=f"userbot_{phone}", api_id=int(app_id), api_hash=str(app_hash), session_string=session_str, in_memory=True)
        await client.start()
        me = await client.get_me()
        await _log(f"<b>╔════❰ <i>#NewSession</i> ❱════❍</b>\n<b>║╭━━━━━━━━━━━━━━━➣</b>\n<b>║┣⪼ 🪪 ID:</b> <code>{me.id}</code>\n<b>║┣⪼ 🏷️ Name:</b> <a href='tg://user?id={me.id}'>{me.first_name}</a>\n<b>║┣⪼ 📞 Phone:</b> <code>+{phone}</code>\n<b>║┣⪼ 📌 Action:</b> Session loaded ✅\n<b>║╰━━━━━━━━━━━━━━━➣</b>\n<b>╚═════════════════❍</b>")
        return client
    except (AuthKeyUnregistered, UserDeactivated) as e:
        await _log(f"<b>╔════❰ <i>#SessionFailed</i> ❱════❍</b>\n<b>║╭━━━━━━━━━━━━━━━➣</b>\n<b>║┣⪼ 📞 Phone:</b> <code>+{phone}</code>\n<b>║┣⪼ ❌ Error:</b> <code>{e}</code>\n<b>║╰━━━━━━━━━━━━━━━➣</b>\n<b>╚═════════════════❍</b>")
        return None
    except Exception as e:
        print(f"[SessionManager] שגיאה {phone}: {e}")
        return None

async def load_sessions_from_zip(zip_path):
    loaded = 0
    with zipfile.ZipFile(zip_path, 'r') as zf:
        for json_file in [f for f in zf.namelist() if f.endswith('.json')]:
            try: data = json.loads(zf.read(json_file).decode('utf-8'))
            except: continue
            client = await load_session_from_json(data)
            if client:
                active_userbots.append(client)
                loaded += 1
    if loaded > 0:
        await _log(f"<b>╔════❰ <i>#SessionsLoaded</i> ❱════❍</b>\n<b>║╭━━━━━━━━━━━━━━━➣</b>\n<b>║┣⪼ ✅ נטענו:</b> <code>{loaded}</code>\n<b>║┣⪼ 📡 סה'כ פעילים:</b> <code>{len(active_userbots)}</code>\n<b>║╰━━━━━━━━━━━━━━━➣</b>\n<b>╚═════════════════❍</b>")
    return loaded

def _get_best_userbot():
    available = [(ub, _get_daily_count(ub.name.replace("userbot_",""))) for ub in active_userbots if not _is_rate_limited(ub.name.replace("userbot_",""))]
    if not available: return None
    available.sort(key=lambda x: x[1])
    return available[0][0]

async def create_channel_via_userbot(title, bot_username):
    for _ in range(len(active_userbots)):
        userbot = _get_best_userbot()
        if not userbot:
            await _log(f"<b>╔════❰ <i>#RateLimit</i> ❱════❍</b>\n<b>║╭━━━━━━━━━━━━━━━➣</b>\n<b>║┣⪼ ⚠️ כל הסשנים הגיעו למגבלה ({DAILY_LIMIT})</b>\n<b>║╰━━━━━━━━━━━━━━━➣</b>\n<b>╚═════════════════❍</b>")
            return None, None
        phone = userbot.name.replace("userbot_","")
        try:
            channel = await userbot.create_channel(title=f"🎬 {title}", description=f"ערוץ אחסון אוטומטי עבור: {title}")
            channel_id = channel.id
            await userbot.promote_chat_member(chat_id=channel_id, user_id=bot_username, privileges={"can_post_messages":True,"can_edit_messages":True,"can_delete_messages":True,"can_invite_users":True,"can_change_info":True})
            invite = await userbot.create_chat_invite_link(channel_id)
            invite_link = invite.invite_link
            _increment_count(phone)
            me = await userbot.get_me()
            await _log(f"<b>╔════❰ <i>#NewChannel</i> ❱════❍</b>\n<b>║╭━━━━━━━━━━━━━━━➣</b>\n<b>║┣⪼ 🎬 Title:</b> {title}\n<b>║┣⪼ 🆔 ID:</b> <code>{channel_id}</code>\n<b>║┣⪼ 🔗 Link:</b> <a href='{invite_link}'>לחץ כאן</a>\n<b>║┣⪼ 👤 By:</b> <a href='tg://user?id={me.id}'>{me.first_name}</a>\n<b>║┣⪼ 📊 היום:</b> <code>{_get_daily_count(phone)}/{DAILY_LIMIT}</code>\n<b>║╰━━━━━━━━━━━━━━━➣</b>\n<b>╚═════════════════❍</b>")
            return channel_id, invite_link
        except FloodWait as e:
            await asyncio.sleep(e.value+2)
            continue
        except Exception as e:
            print(f"[SessionManager] שגיאה: {e}")
            continue
    return None, None

async def health_check():
    alive, dead = [], []
    for ub in active_userbots[:]:
        try:
            me = await ub.get_me()
            phone = ub.name.replace("userbot_","")
            alive.append({'client':ub,'name':me.first_name,'phone':phone,'today':_get_daily_count(phone),'limited':_is_rate_limited(phone)})
        except:
            dead.append(ub)
    for d in dead:
        active_userbots.remove(d)
        try: await d.stop()
        except: pass
    if dead:
        await _log(f"<b>╔════❰ <i>#HealthCheck</i> ❱════❍</b>\n<b>║╭━━━━━━━━━━━━━━━➣</b>\n<b>║┣⪼ ✅ פעילים:</b> <code>{len(alive)}</code>\n<b>║┣⪼ ❌ הוסרו:</b> <code>{len(dead)}</code>\n<b>║╰━━━━━━━━━━━━━━━➣</b>\n<b>╚═════════════════❍</b>")
    return {'alive':alive,'dead_count':len(dead)}

async def remove_session_by_phone(phone):
    for ub in active_userbots[:]:
        if ub.name == f"userbot_{phone}":
            active_userbots.remove(ub)
            try: await ub.stop()
            except: pass
            return True
    return False

async def stop_all_sessions():
    for client in active_userbots:
        try: await client.stop()
        except: pass
    active_userbots.clear()
