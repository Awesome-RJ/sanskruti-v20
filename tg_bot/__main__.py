import datetime
import importlib
import re
from typing import Optional, List

from telegram import Update, Bot
from telegram.constants import ParseMode
from telegram.error import (
    Unauthorized,
    BadRequest,
    TimedOut,
    NetworkError,
    ChatMigrated,
    TelegramError,
)
from telegram.ext import (
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    Application,
    ConversationHandler,
    ContextTypes,
    filters,
)
from telegram.utils.helpers import escape_markdown

# from tg_bot import dispatcher, updater, TOKEN, WEBHOOK, OWNER_ID, DONATION_LINK, CERT_PATH, PORT, URL, LOGGER, ALLOW_EXCL # Removed old imports
# Use os.environ instead of importing constants
import os

# Use the logging module directly
import logging

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
LOGGER = logging.getLogger(__name__)

# Globals
TOKEN = os.environ.get("TOKEN")  # Use os.environ
WEBHOOK = os.environ.get("WEBHOOK", False)  # Use os.environ, default to False if not set
OWNER_ID = int(os.environ.get("OWNER_ID"))  # Use os.environ, convert to int
DONATION_LINK = os.environ.get("DONATION_LINK")  # Use os.environ
CERT_PATH = os.environ.get("CERT_PATH")  # Use os.environ
PORT = int(os.environ.get("PORT", 5000))  # Use os.environ, default to 5000 if not set
URL = os.environ.get("URL")  # Use os.environ
ALLOW_EXCL = os.environ.get("ALLOW_EXCL", False)  # Use os.environ, default to False
# needed to dynamically load modules
# NOTE: Module order is not guaranteed, specify that in the config file!
# from tg_bot.modules import ALL_MODULES # Removed old import
# Use a list directly.  This allows defining module order in main().
ALL_MODULES = [
    "admin",  # Example, add all your modules.  Important to maintain order if you depend on it.
    "antiflood",
    "helper_funcs.chat_status",
    "helper_funcs.misc",
    "help",
    "start",
    "donate",
    "migrate",
    "settings",
    "rules",
]

PM_START_TEXT = """
Hi {}, my name is {}! If you have any questions on how to use me, read /help - and then head to @MarieSupport.

I'm a group manager bot built in python3, using the python-telegram-bot library, and am fully opensource; \
you can find what makes me tick [here](github.com/PaulSonOfLars/tgbot)!

Feel free to submit pull requests on github, or to contact my support group, @MarieSupport, with any bugs, questions \
or feature requests you might have :)
I also have a news channel, @MarieNews for announcements on new features, downtime, etc.

You can find the list of available commands with /help.

If you're enjoying using me, and/or would like to help me survive in the wild, hit /donate to help fund/upgrade my VPS!
"""

HELP_STRINGS = """
Hey there! My name is *{}*.
I'm a modular group management bot with a few fun extras! Have a look at the following for an idea of some of \
the things I can help you with.

*Main* commands available:
  - /start: start the bot
  - /help: PM's you this message.
  - /help <module name>: PM's you info about that module.
  - /donate: information about how to donate!
  - /settings:
    - in PM: will send you your settings for all supported modules.
    - in a group: will redirect you to pm, with all that chat's settings.

{}
And the following:
""".format(
    "{first_name}", "" if not ALLOW_EXCL else "\nAll commands can either be used with / or !.\n"
)  # Corrected formatting.

DONATE_STRING = """Heya, glad to hear you want to donate!
It took lots of work for my creator to get me to where I am now, and every donation helps \
motivate him to make me even better. All the donation money will go to a better VPS to host me, and/or beer \
(see his bio!). He's just a poor student, so every little helps!
There are two ways of paying him; [PayPal](paypal.me/PaulSonOfLars), or [Monzo](monzo.me/paulnionvestergaardlarsen)."""

IMPORTED = {}
MIGRATEABLE = []
HELPABLE = {}
STATS = []
USER_INFO = []
DATA_IMPORT = []
DATA_EXPORT = []

CHAT_SETTINGS = {}
USER_SETTINGS = {}

GDPR = []


# Helper Functions
def load_module(module_name):
    """Loads a module and adds it to the relevant global variables."""
    try:
        imported_module = importlib.import_module("tg_bot.modules." + module_name)
        if not hasattr(imported_module, "__mod_name__"):
            imported_module.__mod_name__ = imported_module.__name__.split(".")[-1]  # Get module name from file

        if imported_module.__mod_name__.lower() in IMPORTED:
            raise Exception("Can't have two modules with the same name! Please change one")

        IMPORTED[imported_module.__mod_name__.lower()] = imported_module

        if hasattr(imported_module, "__help__") and imported_module.__help__:
            HELPABLE[imported_module.__mod_name__.lower()] = imported_module

        if hasattr(imported_module, "__migrate__"):
            MIGRATEABLE.append(imported_module)

        if hasattr(imported_module, "__stats__"):
            STATS.append(imported_module)

        if hasattr(imported_module, "__gdpr__"):
            GDPR.append(imported_module)

        if hasattr(imported_module, "__user_info__"):
            USER_INFO.append(imported_module)

        if hasattr(imported_module, "__import_data__"):
            DATA_IMPORT.append(imported_module)

        if hasattr(imported_module, "__export_data__"):
            DATA_EXPORT.append(imported_module)

        if hasattr(imported_module, "__chat_settings__"):
            CHAT_SETTINGS[imported_module.__mod_name__.lower()] = imported_module

        if hasattr(imported_module, "__user_settings__"):
            USER_SETTINGS[imported_module.__mod_name__.lower()] = imported_module
        return imported_module
    except Exception as e:
        LOGGER.error(f"Error loading module {module_name}: {e}")
        return None  # Important: Return None on failure.


# do not async
async def send_help(chat_id, text, keyboard=None, bot: Bot = None):  # Add bot: Bot
    """Sends a help message."""
    if not keyboard:
        keyboard = InlineKeyboardMarkup(paginate_modules(0, HELPABLE, "help"))
    await bot.send_message(
        chat_id=chat_id, text=text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard
    )


async def test(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Tests the bot."""
    await update.effective_message.reply_text(
        "This person edited a message"
    )  # Removed unused args
    LOGGER.info(update.effective_message)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Starts the bot."""
    bot = context.bot
    if update.effective_chat.type == "private":
        if context.args and len(context.args) >= 1:
            if context.args[0].lower() == "help":
                await send_help(update.effective_chat.id, HELP_STRINGS, bot=bot)  # Pass bot
            elif context.args[0].lower().startswith("stngs_"):
                match = re.match("stngs_(.*)", context.args[0].lower())
                chat = await bot.get_chat(match.group(1))

                # Removed is_user_admin,  using the function from the admin module.
                if await IMPORTED["admin"].is_user_admin(chat, update.effective_user.id):
                    await send_settings(match.group(1), update.effective_user.id, False, bot=bot)
                else:
                    await send_settings(match.group(1), update.effective_user.id, True, bot=bot)

            elif context.args[0][1:].isdigit() and "rules" in IMPORTED:
                await IMPORTED["rules"].send_rules(update, context.args[0], from_pm=True)
        else:
            first_name = update.effective_user.first_name
            await update.effective_message.reply_text(
                PM_START_TEXT.format(
                    escape_markdown(first_name), escape_markdown(bot.first_name)
                ),
                parse_mode=ParseMode.MARKDOWN,
            )
    else:
        await update.effective_message.reply_text("Yo, whadup?")



async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Error handler."""
    # get traceback object
    error = context.error
    try:
        raise error
    except Unauthorized:
        LOGGER.error("Unauthorized: %s", error)
        # remove update.message.chat_id from conversation list
    except BadRequest:
        LOGGER.error("BadRequest: %s", error)
        # handle malformed requests - read more below!
    except TimedOut:
        LOGGER.error("TimedOut: %s", error)
        # handle slow connection problems
    except NetworkError:
        LOGGER.error("NetworkError: %s", error)
        # handle other connection problems
    except ChatMigrated as err:
        LOGGER.error("ChatMigrated: %s", error)
        # the chat_id of a group has changed, use e.new_chat_id instead
    except TelegramError:
        LOGGER.error("TelegramError: %s", error)
        # handle all other telegram related errors
    except Exception:
        LOGGER.exception("Exception while handling update %s", update)



async def help_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Help button callback."""
    query = update.callback_query
    bot = context.bot
    mod_match = re.match(r"help_module\((.+?)\)", query.data)
    prev_match = re.match(r"help_prev\((.+?)\)", query.data)
    next_match = re.match(r"help_next\((.+?)\)", query.data)
    back_match = re.match(r"help_back", query.data)
    try:
        if mod_match:
            module = mod_match.group(1)
            text = "Here is the help for the *{}* module:\n".format(
                HELPABLE[module].__mod_name__
            ) + HELPABLE[module].__help__
            await query.message.reply_text(
                text=text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton(text="Back", callback_data="help_back")]]
                ),
            )

        elif prev_match:
            curr_page = int(prev_match.group(1))
            await query.message.reply_text(
                HELP_STRINGS,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(
                    paginate_modules(curr_page - 1, HELPABLE, "help")
                ),
            )

        elif next_match:
            next_page = int(next_match.group(1))
            await query.message.reply_text(
                HELP_STRINGS,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(
                    paginate_modules(next_page + 1, HELPABLE, "help")
                ),
            )

        elif back_match:
            await query.message.reply_text(
                text=HELP_STRINGS,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(paginate_modules(0, HELPABLE, "help")),
            )

        # ensure no spinny white circle
        await bot.answer_callback_query(query.id)
        await query.message.delete()
    except BadRequest as excp:
        if excp.message == "Message is not modified":
            pass
        elif excp.message == "Query_id_invalid":
            pass
        elif excp.message == "Message can't be deleted":
            pass
        else:
            LOGGER.exception("Exception in help buttons. %s", str(query.data))



async def get_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Gets the help message."""
    chat = update.effective_chat  # type: Optional[Chat]
    args = context.args
    bot = context.bot

    # ONLY send help in PM
    if chat.type != chat.PRIVATE:
        await update.effective_message.reply_text(
            "Contact me in PM to get the list of possible commands.",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            text="Help",
                            url="t.me/{}?start=help".format(bot.username),
                        )
                    ]
                ]
            ),
        )
        return

    elif args and len(args) >= 1 and any(args[0].lower() == x for x in HELPABLE):
        module = args[0].lower()
        text = "Here is the available help for the *{}* module:\n".format(
            HELPABLE[module].__mod_name__
        ) + HELPABLE[module].__help__
        await send_help(
            chat.id,
            text,
            InlineKeyboardMarkup([[InlineKeyboardButton(text="Back", callback_data="help_back")]]),
            bot=bot,
        )

    else:
        await send_help(chat.id, HELP_STRINGS, bot=bot)



async def send_settings(chat_id, user_id, user=False, bot: Bot = None):
    """Sends the settings message."""
    if user:
        if USER_SETTINGS:
            settings = "\n\n".join(
                "*{}*:\n{}".format(mod.__mod_name__, mod.__user_settings__(user_id))
                for mod in USER_SETTINGS.values()
            )
            await bot.send_message(
                user_id,
                "These are your current settings:" + "\n\n" + settings,
                parse_mode=ParseMode.MARKDOWN,
            )

        else:
            await bot.send_message(
                user_id,
                "Seems like there aren't any user specific settings available :'(",
                parse_mode=ParseMode.MARKDOWN,
            )

    else:
        if CHAT_SETTINGS:
            chat_name = (await bot.get_chat(chat_id)).title
            await bot.send_message(
                user_id,
                text="Which module would you like to check {}'s settings for?".format(chat_name),
                reply_markup=InlineKeyboardMarkup(
                    paginate_modules(0, CHAT_SETTINGS, "stngs", chat=chat_id)
                ),
            )
        else:
            await bot.send_message(
                user_id,
                "Seems like there aren't any chat settings available :'(\nSend this "
                "in a group chat you're admin in to find its current settings!",
                parse_mode=ParseMode.MARKDOWN,
            )



async def settings_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Settings button callback."""
    query = update.callback_query
    user = update.effective_user
    bot = context.bot
    mod_match = re.match(r"stngs_module\((.+?),(.+?)\)", query.data)
    prev_match = re.match(r"stngs_prev\((.+?),(.+?)\)", query.data)
    next_match = re.match(r"stngs_next\((.+?),(.+?)\)", query.data)
    back_match = re.match(r"stngs_back\((.+?)\)", query.data)
    try:
        if mod_match:
            chat_id = mod_match.group(1)
            module = mod_match.group(2)
            chat = await bot.get_chat(chat_id)
            text = "*{}* has the following settings for the *{}* module:\n\n".format(
                escape_markdown(chat.title),
                CHAT_SETTINGS[module].__mod_name__,
            ) + CHAT_SETTINGS[module].__chat_settings__(chat_id, user.id)
            await query.message.reply_text(
                text=text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton(text="Back", callback_data="stngs_back({})".format(chat_id))]]
                ),
            )

        elif prev_match:
            chat_id = prev_match.group(1)
            curr_page = int(prev_match.group(2))
            chat = await bot.get_chat(chat_id)
            await query.message.reply_text(
                "Hi there! There are quite a few settings for {} - go ahead and pick what "
                "you're interested in.".format(chat.title),
                reply_markup=InlineKeyboardMarkup(
                    paginate_modules(curr_page - 1, CHAT_SETTINGS, "stngs", chat=chat_id)
                ),
            )

        elif next_match:
            chat_id = next_match.group(1)
            next_page = int(next_match.group(2))
            chat = await bot.get_chat(chat_id)
            await query.message.reply_text(
                "Hi there! There are quite a few settings for {} - go ahead and pick what "
                "you're interested in.".format(chat.title),
                reply_markup=InlineKeyboardMarkup(
                    paginate_modules(next_page + 1, CHAT_SETTINGS, "stngs", chat=chat_id)
                ),
            )

        elif back_match:
            chat_id = back_match.group(1)
            chat = await bot.get_chat(chat_id)
            await query.message.reply_text(
                text="Hi there! There are quite a few settings for {} - go ahead and pick what "
                "you're interested in.".format(escape_markdown(chat.title)),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(
                    paginate_modules(0, CHAT_SETTINGS, "stngs", chat=chat_id)
                ),
            )

        # ensure no spinny white circle
        await bot.answer_callback_query(query.id)
        await query.message.delete()
    except BadRequest as excp:
        if excp.message == "Message is not modified":
            pass
        elif excp.message == "Query_id_invalid":
            pass
        elif excp.message == "Message can't be deleted":
            pass
        else:
            LOGGER.exception("Exception in settings buttons. %s", str(query.data))



async def get_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Gets the settings."""
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    msg = update.effective_message  # type: Optional[Message]
    args = context.args
    bot = context.bot

    # ONLY send settings in PM
    if chat.type != chat.PRIVATE:
        if await IMPORTED["admin"].is_user_admin(chat, user.id):  # Use admin module function
            text = "Click here to get this chat's settings, as well as yours."
            await msg.reply_text(
                text,
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                text="Settings",
                                url="t.me/{}?start=stngs_{}".format(bot.username, chat.id),
                            )
                        ]
                    ]
                ),
            )
        else:
            text = "Click here to check your settings."

    else:
        await send_settings(chat.id, user.id, True, bot=bot)



async def donate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles donations."""
    user = update.effective_message.from_user
    chat = update.effective_chat  # type: Optional[Chat]
    bot = context.bot

    if chat.type == "private":
        await update.effective_message.reply_text(
            DONATE_STRING, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True
        )

        if OWNER_ID != 254318997 and DONATION_LINK:
            await update.effective_message.reply_text(
                "You can also donate to the person currently running me "
                "[here]({})".format(DONATION_LINK),
                parse_mode=ParseMode.MARKDOWN,
            )

    else:
        try:
            await bot.send_message(
                user.id, DONATE_STRING, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True
            )

            await update.effective_message.reply_text("I've PM'ed you about donating to my creator!")
        except Unauthorized:
            await update.effective_message.reply_text("Contact me in PM first to get donation information.")



async def migrate_chats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles chat migrations."""
    msg = update.effective_message  # type: Optional[Message]
    if msg.migrate_to_chat_id:
        old_chat = update.effective_chat.id
        new_chat = msg.migrate_to_chat_id
    elif msg.migrate_from_chat_id:
        old_chat = msg.migrate_from_chat_id
        new_chat = update.effective_chat.id
    else:
        return

    LOGGER.info("Migrating from %s, to %s", str(old_chat), str(new_chat))
    for mod in MIGRATEABLE:
        await mod.__migrate__(old_chat, new_chat, context.bot)  # Pass the bot instance.

    LOGGER.info("Successfully migrated!")
    raise ConversationHandler.END  # Use ConversationHandler.END



def paginate_modules(page_n, module_dict, prefix, chat=None):
    """Paginates modules."""
    if not module_dict:
        return []
    items_per_page = 5
    names = sorted(module_dict.keys())
    pages = [names[i : i + items_per_page] for i in range(0, len(names), items_per_page)]
    num_pages = len(pages)

    curr_page = pages[page_n]
    if not curr_page:
        return []

    kbrd = []
    for mod in curr_page:
        if mod == "admin" and chat: #check if the module is admin
          kbrd.append([InlineKeyboardButton(module_dict[mod].__mod_name__, callback_data=f"{prefix}_module({chat},{mod})")])
        elif mod == "admin":
           kbrd.append([InlineKeyboardButton(module_dict[mod].__mod_name__, callback_data=f"{prefix}_module({mod})")])
        elif chat:
            kbrd.append(
                [
                    InlineKeyboardButton(
                        module_dict[mod].__mod_name__, callback_data=f"{prefix}_module({chat.id},{mod})"
                    )
                ]
            )
        else:
            kbrd.append(
                [
                    InlineKeyboardButton(
                        module_dict[mod].__mod_name__, callback_data=f"{prefix}_module({mod})"
                    )
                ]
            )

    if page_n > 0:
        if chat:
          kbrd.append([InlineKeyboardButton("Previous", callback_data=f"{prefix}_prev({chat.id},{page_n - 1})")])
        else:
          kbrd.append([InlineKeyboardButton("Previous", callback_data=f"{prefix}_prev({page_n - 1})")])
    if page_n < num_pages - 1:
        if chat:
          kbrd.append([InlineKeyboardButton("Next", callback_data=f"{prefix}_next({chat.id},{page_n + 1})")])
        else:
          kbrd.append([InlineKeyboardButton("Next", callback_data=f"{prefix}_next({page_n + 1})")])
    return kbrd



async def main() -> None:
    """Main function."""

    # Create the Application and pass it your bot's token.
    application = Application.builder().token(TOKEN).build()
    # application.job_queue.run_once() # Removed -  Not used

    # Load modules
    for module_name in ALL_MODULES:  # Use the defined list.
        loaded_module = load_module(module_name)
        if loaded_module:
            LOGGER.info(f"Successfully loaded module: {module_name}")

    # Handlers
    # application.add_handler(test_handler) # Removed - defined below
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", get_help))
    application.add_handler(CallbackQueryHandler(help_button, pattern=r"help_"))
    application.add_handler(CommandHandler("settings", get_settings))
    application.add_handler(CallbackQueryHandler(settings_button, pattern=r"stngs_"))
    application.add_handler(CommandHandler("donate", donate))
    application.add_handler(MessageHandler(filters.StatusUpdate.MIGRATE, migrate_chats))  # Corrected filter
    application.add_error_handler(error_handler)

    # Add individual handlers for each module.  This is the new way in PTB 20.
    for module_name, loaded_module in IMPORTED.items():
        if hasattr(loaded_module, "handlers"):
            handlers = loaded_module.handlers()  # Get handlers
            if isinstance(handlers, list):
                for handler in handlers:
                    application.add_handler(handler)
            else:
                application.add_handler(handlers) # Add single handler

    # Add test handler
    application.add_handler(CommandHandler("test", test))

    # Run the app
    if WEBHOOK:
        LOGGER.info("Using webhooks.")
        await application.bot.set_webhook(url=URL + TOKEN)
        # Use aiohttp.web.Application
        # web_app = application.application  # Get the aiohttp application
        # from aiohttp import web
        # web.run_app(web_app, host="127.0.0.1", port=PORT) # removed aiohttp
        webhook_url = URL + TOKEN
        await application.bot.set_webhook(url=webhook_url, certificate=CERT_PATH if CERT_PATH else None)
        start_receiver = application.start_webhook(
            listen="0.0.0.0",  # Listen on all interfaces
            port=int(PORT),
            webhook_url=webhook_url,
            certificate=CERT_PATH if CERT_PATH else None,
        )
        async with application:
            await application.start()
            await start_receiver
            await application.idle()
            await application.stop()

    else:
        LOGGER.info("Using long polling.")
        await application.start_polling()
        await application.idle()


if __name__ == "__main__":
    LOGGER.info("Starting bot...")
    import asyncio

    asyncio.run(main())
