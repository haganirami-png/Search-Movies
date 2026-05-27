import json, re, asyncio, os, zipfile
from pyrogram import Client
from pyrogram.errors import FloodWait

DB_CHANNEL_TITLE = "🗄 Bot Database"
DB_CHANNEL_ID_FILE = "db_channel_id.txt"

class ChannelDB:
    def __init__(self):
        self._bot = None
        self._channel_id = None
        self._prefix = "bot"
        self._files_cache = []
        self._users_cache = {}
        self._groups_cache = {}
        self._settings_cache = {}
        self._watched_cache = set()
        self._banned_cache = {}
        self._banned_chats_cache = {}
        self._media_channels_cache = {}
        self._files_msg_id = None
        self._users_msg_id = None
        self._groups_msg_id = None
        self._settings_msg_id = None
        self._watched_msg_id = None
        self._banned_msg_id = None
        self._media_ch_msg_id = None

    async def init_database(self, bot):
        self._bot = bot
        me = await bot.get_me()
        self._prefix = me.username
        if os.path.exists(DB_CHANNEL_ID_FILE):
            with open(DB_CHANNEL_ID_FILE) as f:
                self._channel_id = int(f.read().strip())
            await self._load_all()
        print("[ChannelDB] ✅ מוכן")

    async def ensure_db_channel(self):
        if self._channel_id:
            return True
        from session_manager import active_userbots
        if not active_userbots:
            return False
        userbot = active_userbots[0]
        try:
            channel = await userbot.create_channel(title=DB_CHANNEL_TITLE)
            channel_id = channel.id
            me = await self._bot.get_me()
            await userbot.promote_chat_member(chat_id=channel_id, user_id=me.username, privileges={"can_post_messages":True,"can_edit_messages":True,"can_delete_messages":True,"can_invite_users":True,"can_change_info":True})
            with open(DB_CHANNEL_ID_FILE, 'w') as f:
                f.write(str(channel_id))
            self._channel_id = channel_id
            print(f"[ChannelDB] ✅ ערוץ DB נוצר: {channel_id}")
            return True
        except Exception as e:
            print(f"[ChannelDB] שגיאה: {e}")
            return False

    async def _load_all(self):
        if not self._channel_id: return
        async for msg in self._bot.get_chat_history(self._channel_id):
            if not msg.text: continue
            text = msg.text
            try:
                if text.startswith("#FILES"):
                    self._files_cache = json.loads(text[7:])
                    self._files_msg_id = msg.id
                elif text.startswith("#USERS"):
                    self._users_cache = {int(k):v for k,v in json.loads(text[7:]).items()}
                    self._users_msg_id = msg.id
                elif text.startswith("#GROUPS"):
                    self._groups_cache = {int(k):v for k,v in json.loads(text[8:]).items()}
                    self._groups_msg_id = msg.id
                elif text.startswith("#SETTINGS"):
                    self._settings_cache = {int(k):v for k,v in json.loads(text[10:]).items()}
                    self._settings_msg_id = msg.id
                elif text.startswith("#WATCHED"):
                    self._watched_cache = set(json.loads(text[9:]))
                    self._watched_msg_id = msg.id
                elif text.startswith("#BANNED"):
                    self._banned_cache = {int(k):v for k,v in json.loads(text[8:]).items()}
                    self._banned_msg_id = msg.id
                elif text.startswith("#MEDIACH"):
                    self._media_channels_cache = json.loads(text[9:])
                    self._media_ch_msg_id = msg.id
            except: continue

    async def _save(self, tag, data, msg_id_attr):
        if not self._channel_id: return
        text = f"#{tag}\n{json.dumps(data, ensure_ascii=False)}"
        msg_id = getattr(self, msg_id_attr)
        try:
            if msg_id:
                await self._bot.edit_message_text(self._channel_id, msg_id, text)
            else:
                msg = await self._bot.send_message(self._channel_id, text)
                setattr(self, msg_id_attr, msg.id)
        except FloodWait as e:
            await asyncio.sleep(e.value+1)
            await self._save(tag, data, msg_id_attr)
        except Exception as e:
            print(f"[DB] שגיאה {tag}: {e}")

    async def save_file(self, file_data):
        from Tj_Bots.caption_builder import parse_caption
        for f in self._files_cache:
            if f.get('file_unique_id') == file_data['file_unique_id']:
                return "duplicate"
        new_info = parse_caption(file_data.get('caption',''), file_data.get('file_name',''))
        new_title = new_info.get('title','').strip().lower()
        new_season = new_info.get('season')
        new_episode = new_info.get('episode')
        if new_title:
            for f in self._files_cache:
                old_info = parse_caption(f.get('caption',''), f.get('file_name',''))
                old_title = old_info.get('title','').strip().lower()
                if old_title != new_title: continue
                if new_season and new_episode:
                    if old_info.get('season') == new_season and old_info.get('episode') == new_episode:
                        return "duplicate"
                else:
                    return "duplicate"
        self._files_cache.append(file_data)
        await self._save("FILES", self._files_cache, "_files_msg_id")
        return "saved"

    async def get_file(self, _id):
        for f in self._files_cache:
            if str(f.get('_id','')) == _id or str(f.get('file_unique_id','')) == _id:
                return f
        try: return self._files_cache[int(_id)]
        except: return None

    async def search_files(self, query):
        clean = re.sub(r'[._\-]', ' ', query)
        words = clean.split()
        results = [f for f in self._files_cache if all(re.search(re.escape(w), f.get('file_name',''), re.IGNORECASE) for w in words)]
        def sort_key(item):
            name = item.get('file_name','')
            s = re.search(r'(?:עונה|season|s)\s*(\d+)', name, re.I)
            e = re.search(r'(?:פרק|episode|e)\s*(\d+)', name, re.I)
            return (int(s.group(1)) if s else 0, int(e.group(1)) if e else 0)
        results.sort(key=sort_key)
        return results

    async def delete_all_files(self):
        count = len(self._files_cache)
        self._files_cache = []
        await self._save("FILES", [], "_files_msg_id")
        return count

    async def add_user(self, user_id, first_name):
        if user_id in self._users_cache: return False
        self._users_cache[user_id] = {'first_name': first_name}
        await self._save("USERS", {str(k):v for k,v in self._users_cache.items()}, "_users_msg_id")
        return True

    async def get_all_users(self): return list(self._users_cache.items())
    async def delete_all_users(self):
        count = len(self._users_cache)
        self._users_cache = {}
        await self._save("USERS", {}, "_users_msg_id")
        return count

    async def add_group(self, chat_id, title):
        if chat_id in self._groups_cache: return False
        self._groups_cache[chat_id] = {'title': title}
        await self._save("GROUPS", {str(k):v for k,v in self._groups_cache.items()}, "_groups_msg_id")
        return True

    async def get_all_groups(self): return list(self._groups_cache.items())
    async def delete_all_groups(self):
        count = len(self._groups_cache)
        self._groups_cache = {}
        await self._save("GROUPS", {}, "_groups_msg_id")
        return count

    async def get_settings(self, chat_id):
        return self._settings_cache.get(chat_id, {'results_per_page':10,'display_mode':'inline','search_trigger':'all','show_image':True})

    async def update_settings(self, chat_id, key, value):
        if chat_id not in self._settings_cache: self._settings_cache[chat_id] = {}
        self._settings_cache[chat_id][key] = value
        await self._save("SETTINGS", {str(k):v for k,v in self._settings_cache.items()}, "_settings_msg_id")

    async def add_watched_channel(self, chat_id):
        self._watched_cache.add(chat_id)
        await self._save("WATCHED", list(self._watched_cache), "_watched_msg_id")

    async def remove_watched_channel(self, chat_id):
        self._watched_cache.discard(chat_id)
        await self._save("WATCHED", list(self._watched_cache), "_watched_msg_id")

    async def get_watched_channels(self): return list(self._watched_cache)

    async def ban_user(self, user_id, reason="לא צוינה"):
        self._banned_cache[user_id] = {'reason': reason}
        await self._save("BANNED", {str(k):v for k,v in self._banned_cache.items()}, "_banned_msg_id")

    async def unban_user(self, user_id):
        self._banned_cache.pop(user_id, None)
        await self._save("BANNED", {str(k):v for k,v in self._banned_cache.items()}, "_banned_msg_id")

    async def get_ban_status(self, user_id): return self._banned_cache.get(user_id)
    async def ban_chat(self, chat_id, reason="לא צוינה"): self._banned_chats_cache[chat_id] = {'reason': reason}
    async def unban_chat(self, chat_id): self._banned_chats_cache.pop(chat_id, None)
    async def get_chat_ban_status(self, chat_id): return self._banned_chats_cache.get(chat_id)

    async def get_media_channel(self, title): return self._media_channels_cache.get(title)
    async def save_media_channel(self, title, channel_id, invite_link):
        self._media_channels_cache[title] = {'channel_id': channel_id, 'invite_link': invite_link}
        await self._save("MEDIACH", self._media_channels_cache, "_media_ch_msg_id")

    async def get_all_media_channels(self): return [{'_id':k,**v} for k,v in self._media_channels_cache.items()]

    @property
    def files(self): return _FakeCollection(self._files_cache)
    @property
    def users(self): return _FakeCollection(list(self._users_cache.values()))
    @property
    def groups(self): return _FakeCollection(list(self._groups_cache.values()))
    @property
    def banned(self): return _FakeCollection(list(self._banned_cache.values()))
    @property
    def db(self): return _FakeDB(self)

class _FakeCollection:
    def __init__(self, data): self._data = data
    async def count_documents(self, _=None): return len(self._data)

class _FakeDB:
    def __init__(self, cdb): self._cdb = cdb
    def __getitem__(self, key): return _FakeMediaChannelCollection(self._cdb)

class _FakeMediaChannelCollection:
    def __init__(self, cdb): self._cdb = cdb
    async def count_documents(self, _=None): return len(self._cdb._media_channels_cache)
    async def find(self, _=None): return _FakeCursor(await self._cdb.get_all_media_channels())
    async def find_one(self, q): return self._cdb._media_channels_cache.get(q.get('_id'))
    async def update_one(self, q, u, upsert=False):
        self._cdb._media_channels_cache[q.get('_id')] = u.get('$set',{})
        await self._cdb._save("MEDIACH", self._cdb._media_channels_cache, "_media_ch_msg_id")
    async def delete_many(self, _=None):
        count = len(self._cdb._media_channels_cache)
        self._cdb._media_channels_cache = {}
        await self._cdb._save("MEDIACH", {}, "_media_ch_msg_id")
        return _FakeDeleteResult(count)

class _FakeCursor:
    def __init__(self, data): self._data = data
    async def to_list(self, length=None): return self._data

class _FakeDeleteResult:
    def __init__(self, count): self.deleted_count = count

db = ChannelDB()
