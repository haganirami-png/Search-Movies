import os
import requests
import json
from pyrogram import Client, filters

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.104 Safari/537.36",
    "content-type": "application/json",
}

def p_paste(message, extension="txt"):
    siteurl = "https://paste.kaizoku.cyou/api/v1/pastes"
    data = {"content": message}
    try:
        response = requests.post(url=siteurl, data=json.dumps(data), headers=headers)
        if response.ok:
            resp_json = response.json()
            purl = f"https://paste.kaizoku.cyou/{resp_json['id']}.{extension}"
            return {
                "url": purl,
                "raw": f"https://paste.kaizoku.cyou/{resp_json['id']}/raw",
                "status": True
            }
        return {"status": False, "error": "Unable to reach pasty.lus.pm"}
    except Exception as e:
        return {"status": False, "error": str(e)}

@Client.on_message(filters.command(["paste", "pasty", "tgpaste"]))
async def paste_handler(client, message):
    status_msg = await message.reply("⏳ **מעבד טקסט...**", quote=True)
    
    content = ""
    
    if len(message.command) > 1:
        content = message.text.split(None, 1)[1]
    
    elif message.reply_to_message:
        if message.reply_to_message.document:
            if message.reply_to_message.document.file_size > 1048576:
                return await status_msg.edit("✘ הקובץ גדול מדי (מקסימום 1MB).")
            
            await status_msg.edit("⏳ **מוריד קובץ...**")
            try:
                file_path = await message.reply_to_message.download()
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                os.remove(file_path)
            except Exception as e:
                return await status_msg.edit(f"✘ שגיאה בקריאת הקובץ: {e}")
        
        elif message.reply_to_message.text or message.reply_to_message.caption:
            content = message.reply_to_message.text or message.reply_to_message.caption

    if not content:
        return await status_msg.edit("✘ **לא נמצא תוכן.**\nהגב על הודעת טקסט/קובץ או כתוב את הטקסט ליד הפקודה.")

    await status_msg.edit("📤 **מעלה ל-Pastebin...**")
    
    ext = "" 
    if message.reply_to_message and message.reply_to_message.document:
        try: ext = message.reply_to_message.document.file_name.split(".")[-1]
        except: pass

    result = p_paste(content, ext)
    
    if result["status"]:
        p_link = result["url"]
        p_raw = result["raw"]
        
        text = (
            "**[✓] הועלה בהצלחה ל-Pasty**\n\n"
            f"**➲ Link:**\n<blockquote>{p_link}</blockquote>\n\n"
            f"**➲ RAW:**\n<blockquote>{p_raw}.</blockquote>"
        )
        await status_msg.edit(text, disable_web_page_preview=True)
    else:
        await status_msg.edit(f"✘ שגיאה בהעלאה: {result['error']}")
