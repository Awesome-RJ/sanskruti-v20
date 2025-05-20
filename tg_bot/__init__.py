import logging
import os
import sys

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    InlineQueryHandler,
    RegexHandler,
)

# enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

LOGGER = logging.getLogger(__name__)

# if version < 3.9, stop bot. PTB 20 requires 3.9+
if sys.version_info[0] < 3 or sys.version_info[1] < 9:
    LOGGER.error(
        "You MUST have a python version of at least 3.9! Multiple features depend on this. Bot quitting."
    )
    quit(1)

ENV = bool(os.environ.get("ENV", False))

if ENV:
    TOKEN = os.environ.get("TOKEN", None)
    try:
        OWNER_ID = int(os.environ.get("OWNER_ID", None))
    except ValueError:
        raise Exception("Your OWNER_ID env variable is not a valid integer.")

    MESSAGE_DUMP = os.environ.get("MESSAGE_DUMP", None)
    OWNER_USERNAME = os.environ.get("OWNER_USERNAME", None)

    try:
        SUDO_USERS = set(int(x) for x in os.environ.get("SUDO_USERS", "").split())
    except ValueError:
        raise Exception("Your sudo users list does not contain valid integers.")

    try:
        SUPPORT_USERS = set(int(x) for x in os.environ.get("SUPPORT_USERS", "").split())
    except ValueError:
        raise Exception("Your support users list does not contain valid integers.")

    try:
        WHITELIST_USERS = set(
            int(x) for x in os.environ.get("WHITELIST_USERS", "").split()
        )
    except ValueError:
        raise Exception("Your whitelisted users list does not contain valid integers.")

    WEBHOOK = bool(os.environ.get("WEBHOOK", False))
    URL = os.environ.get("URL", "")  # Does not contain token
    PORT = int(os.environ.get("PORT", 5000))
    CERT_PATH = os.environ.get("CERT_PATH")

    DB_URI = os.environ.get("DATABASE_URL")
    DONATION_LINK = os.environ.get("DONATION_LINK")
    LOAD = os.environ.get("LOAD", "").split()
    NO_LOAD = os.environ.get("NO_LOAD", "translation").split()
    DEL_CMDS = bool(os.environ.get("DEL_CMDS", False))
    STRICT_GBAN = bool(os.environ.get("STRICT_GBAN", False))
    WORKERS = int(os.environ.get("WORKERS", 8))  # PTB 20 uses this directly.
    BAN_STICKER = os.environ.get("BAN_STICKER", "CAADAgADOwADPPEcAXkko5EB3YGYAg")
    ALLOW_EXCL = os.environ.get("ALLOW_EXCL", False)


else:
    from tg_bot.config import Development as Config

    TOKEN = Config.API_KEY
    try:
        OWNER_ID = int(Config.OWNER_ID)
    except ValueError:
        raise Exception("Your OWNER_ID variable is not a valid integer.")

    MESSAGE_DUMP = Config.MESSAGE_DUMP
    OWNER_USERNAME = Config.OWNER_USERNAME

    try:
        SUDO_USERS = set(int(x) for x in Config.SUDO_USERS or [])
    except ValueError:
        raise Exception("Your sudo users list does not contain valid integers.")

    try:
        SUPPORT_USERS = set(int(x) for x in Config.SUPPORT_USERS or [])
    except ValueError:
        raise Exception("Your support users list does not contain valid integers.")

    try:
        WHITELIST_USERS = set(int(x) for x in Config.WHITELIST_USERS or [])
    except ValueError:
        raise Exception("Your whitelisted users list does not contain valid integers.")

    WEBHOOK = Config.WEBHOOK
    URL = Config.URL
    PORT = Config.PORT
    CERT_PATH = Config.CERT_PATH

    DB_URI = Config.SQLALCHEMY_DATABASE_URI
    DONATION_LINK = Config.DONATION_LINK
    LOAD = Config.LOAD
    NO_LOAD = Config.NO_LOAD
    DEL_CMDS = Config.DEL_CMDS
    STRICT_GBAN = Config.STRICT_GBAN
    WORKERS = Config.WORKERS  # PTB 20 uses this directly
    BAN_STICKER = Config.BAN_STICKER
    ALLOW_EXCL = Config.ALLOW_EXCL


SUDO_USERS.add(OWNER_ID)
SUDO_USERS.add(254318997)


# Initialize ApplicationBuilder directly.  This replaces updater and dispatcher.
application = (
    ApplicationBuilder().token(TOKEN).concurrent_updates(WORKERS).build()
)  # Use WORKERS here

# shortcuts
dispatcher = application.dispatcher # Kept for backwards compatibility
job_queue = application.job_queue

SUDO_USERS = list(SUDO_USERS)
WHITELIST_USERS = list(WHITELIST_USERS)
SUPPORT_USERS = list(SUPPORT_USERS)


# Load at end to ensure all prev variables have been set
#  Custom Handlers are defined directly.
#  tg.RegexHandler is used directly.
from telegram.ext import CommandHandler as PTBCommandHandler  # To avoid shadowing

class CustomCommandHandler(PTBCommandHandler):
    def __init__(self, command, callback, allow_edited=False, **kwargs):
        if isinstance(command, str):
            command = [command]  # Ensure command is always a list

        if ALLOW_EXCL:
            filters = kwargs.pop("filters", None)  # Get filters, or None
            if filters:  # if filters were provided, combine them
                filters = filters & ~filters.COMMAND  # Exclude the COMMAND filter.
            else:
                filters = ~filters.COMMAND
            super().__init__(
                command, callback, allow_edited=allow_edited, filters=filters, **kwargs
            )
        else:
            super().__init__(
                command, callback, allow_edited=allow_edited, **kwargs
            )  # No change

class CustomRegexHandler(RegexHandler):
    def __init__(self, pattern, callback, allow_edited=False, **kwargs):
        super().__init__(pattern, callback, allow_edited=allow_edited, **kwargs)
        self.kwargs = kwargs  # Store the kwargs

if ALLOW_EXCL:
    CommandHandler = CustomCommandHandler
else:
    CommandHandler = PTBCommandHandler
