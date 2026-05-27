from os import environ

API_ID   = int(environ.get("API_ID", 0))
API_HASH = environ.get("API_HASH", "")
BOT_TOKEN = environ.get("BOT_TOKEN", "")
ADMINS   = list(map(int, environ.get("ADMINS", "0").split()))
LOG_CHANNEL  = int(environ.get("LOG_CHANNEL", 0))
UPDATE_CHANNEL = environ.get("UPDATE_CHANNEL", "")
REQUEST_GROUP  = environ.get("REQUEST_GROUP", "")
PHOTO_URL      = environ.get("PHOTO_URL", "")
AUTH_CHANNEL_FORCE = environ.get("AUTH_CHANNEL_FORCE", "False") == "True"
