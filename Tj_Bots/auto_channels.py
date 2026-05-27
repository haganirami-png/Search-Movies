import re, asyncio
from pyrogram.errors import FloodWait

def extract_title(file_name):
    name = re.sub(r'\.\w{2,4}$', '', file_name)
    stopwords = r'(S\d{1,2}[\.\s]?E\d{1,2}|Season|עונה|Episode|פרק|\b\d{4}\b|\d{3,4}p|BluRay|WEBRip|WEB-DL|HDTV|x264|x265|HEVC|AAC|AC3)'
    match = re.search(stopwords, name, re.IGNORECASE)
    if match: name = name[:match.start()]
    name = re.sub(r'[._\-]+', ' ', name).strip()
    name = re.sub(r'\s+', ' ', name).strip()
    return name if name else file_name

async def get_or_create_media_channel(client, db, title):
    col = db.db[f"{db._prefix}_media_channels"]
    existing = await col.find_one({'_id': title})
    if existing: return existing
    from session_manager import create_channel_via_userbot
    me = await client.get_me()
    channel_id, invite_link = await create_channel_via_userbot(title, me.username)
    if not channel_id: return None
    doc = {'channel_id': channel_id, 'invite_link': invite_link}
    await col.update_one({'_id': title}, {'$set': doc}, upsert=True)
    return doc

async def forward_file_to_channel(client, db, file_data):
    from Tj_Bots.caption_builder import build_caption
    title = extract_title(file_data.get('file_name', ''))
    channel_info = await get_or_create_media_channel(client, db, title)
    if not channel_info: return None
    try:
        caption = build_caption(file_data.get('caption', ''), file_data.get('file_name', ''))
        await client.copy_message(
            chat_id=channel_info['channel_id'],
            from_chat_id=file_data['chat_id'],
            message_id=file_data['message_id'],
            caption=caption,
            parse_mode="html"
        )
        return channel_info['invite_link']
    except FloodWait as e:
        await asyncio.sleep(e.value+2)
        return None
    except Exception as e:
        print(f"[AutoChannel] שגיאה: {e}")
        return None
