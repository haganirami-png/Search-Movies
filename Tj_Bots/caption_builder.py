import re

CHANNEL_LINK = "https://t.me/+c4BT_ECw7qA5ZDE0"
CHANNEL_CREDIT = "העולה על ידי POPIL בטלגרם"

def parse_caption(raw_caption, file_name=""):
    text = raw_caption or file_name or ""
    result = {'title':'','year':None,'season':None,'episode':None,'dub_type':None}
    year_match = re.search(r'[-–]\s*(\d{4})', text)
    if year_match:
        result['year'] = year_match.group(1)
        result['title'] = text[:year_match.start()].strip()
    else:
        year_inline = re.search(r'\b(19\d{2}|20\d{2})\b', text)
        if year_inline:
            result['year'] = year_inline.group(1)
    if not result['title']:
        first_line = text.split('\n')[0].strip()
        first_line = re.sub(r'\b(19\d{2}|20\d{2})\b','',first_line)
        first_line = re.sub(r'[-–]','',first_line).strip()
        result['title'] = first_line
    se_match = re.search(r'[Ss](\d{1,2})[Ee](\d{1,2})', text)
    season_match = re.search(r'(?:עונה|season|s)\s*(\d+)', text, re.IGNORECASE)
    episode_match = re.search(r'(?:פרק|episode|e)\s*(\d+)', text, re.IGNORECASE)
    if se_match:
        result['season'] = int(se_match.group(1))
        result['episode'] = int(se_match.group(2))
    else:
        if season_match: result['season'] = int(season_match.group(1))
        if episode_match: result['episode'] = int(episode_match.group(1))
    if re.search(r'מדובב', text): result['dub_type'] = 'מדובב'
    elif re.search(r'תרגום מובנה', text): result['dub_type'] = 'תרגום מובנה'
    elif re.search(r'תרגום', text): result['dub_type'] = 'תרגום'
    return result

def build_caption(raw_caption, file_name=""):
    info = parse_caption(raw_caption, file_name)
    lines = []
    if info['title']: lines.append(f"<b>{info['title']}</b>")
    lines.append("")
    if info['year']: lines.append(f"📅 {info['year']}")
    if info['season'] and info['episode']: lines.append(f"📺 עונה {info['season']} פרק {info['episode']}")
    elif info['season']: lines.append(f"📺 עונה {info['season']}")
    elif info['episode']: lines.append(f"📺 פרק {info['episode']}")
    if info['dub_type']: lines.append(f"🎙 {info['dub_type']}")
    lines.append("")
    lines.append(CHANNEL_CREDIT)
    lines.append(CHANNEL_LINK)
    return "\n".join(lines)
