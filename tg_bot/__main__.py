import asyncio
import datetime
import importlib
import re
from typing import Optional, List, Tuple, Union

from telegram import Update, Bot, User, Chat
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

# from tg_bot import dispatcher, updater, TOKEN, WEBHOOK, OWNER_ID, DONATION_LINK, CERT_PATH, PORT, URL, LOGGER, ALLOW_EXCL
# Use os.environ instead of importing constants.  This is more secure and flexible.
import os

# Use a logger
import logging

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
LOGGER = logging.getLogger(__name__)

# needed to dynamically load modules
# NOTE: Module order is not guaranteed, specify that in the config file!
# from tg_bot.modules import ALL_MODULES
# Use a list directly.  Much simpler.
ALL_MODULES = [
    "admin",  # Example, add all your module names here.  Don't include the full path.
    "antiflood",
    "rules",
    "helper_funcs.chat_status",
    "helper_funcs.misc"
    # Add all your module names here
]

# You can define these constants directly, or preferrably, get them from environment variables.
TOKEN = os.environ.get("TOKEN")  # Mandatory
WEBHOOK = os.environ.get("WEBHOOK", False)  # Optional, defaults to False
OWNER_ID = int(os.environ.get("OWNER_ID"))  # Mandatory
DONATION_LINK = os.environ.get("DONATION_LINK")  # Optional
CERT_PATH = os.environ.get("CERT_PATH")  # Optional
PORT = int(os.environ.get("PORT", 5000))  # Optional, defaults to 5000
URL = os.environ.get("URL")  # Optional, required if using webhooks
ALLOW_EXCL = os.environ.get("ALLOW_EXCL", False)  # Optional, defaults to False


PM_START_TEXT = """
Hi {}, my name is {}! If you have any questions on how to use me, read /help - and then head to @MarieSupport.

I'm a group manager bot built in python, using the python-telegram-bot library, and am fully opensource;
you can find what makes me tick [here](github.com/PaulSonOfLars/tgbot)!

Feel free to submit pull requests on github, or to contact my support group, @MarieSupport, with any bugs, questions
or feature requests you might have :)
I also have a news channel, @MarieNews for announcements on new features, downtime, etc.

You can find the list of available commands with /help.

If you're enjoying using me, and/or would like to help me survive in the wild, hit /donate to help fund/upgrade my VPS!
"""

HELP_STRINGS = """
Hey there! My name is *{}*.
I'm a modular group management bot with a few fun extras! Have a look at the following for an idea of some of
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
    "{{bot_name}}", "" if not ALLOW_EXCL else "\nAll commands can either be used with / or !.\n"
)

DONATE_STRING = """Heya, glad to hear you want to donate!
It took lots of work for my creator to get me to where I am now, and every donation helps
motivate him to make me even better. All the donation money will go to a better VPS to host me, and/or beer
(see his bio!). He's just a poor student, so every little helps!
There are two ways of paying him; [PayPal](paypal.me/PaulSonOfLars), or [Monzo](monzo.me/paulnionvestergaardlarsen).
"""

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


async def load_modules():
    """Dynamically loads modules."""
    for module_name in ALL_MODULES:
        try:
            imported_module = importlib.import_module(
                "tg_bot.modules." + module_name
            )  # Corrected import path
            if not hasattr(imported_module, "__mod_name__"):
                imported_module.__mod_name__ = module_name

            if imported_module.__mod_name__.lower() not in IMPORTED:
                IMPORTED[imported_module.__mod_name__.lower()] = imported_module
            else:
                raise Exception(
                    "Can't have two modules with the same name! Please change one"
                )

            if (
                hasattr(imported_module, "__help__")
                and imported_module.__help__
            ):
                HELPABLE[imported_module.__mod_name__.lower()] = imported_module

            # Chats to migrate on chat_migrated events
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

        except ImportError as e:
            LOGGER.warning("Error importing module %s: %s", module_name, e)
        except Exception as e:
            LOGGER.error("Failed to load module %s: %s", module_name, e)
            # Consider exiting if a critical module fails to load
            # raise e # uncomment if you want the bot to stop on error.

    LOGGER.info("Modules loaded: %s", list(IMPORTED.keys()))



async def send_help(chat_id: int, text: str, keyboard=None, bot: Bot = None) -> None:
    """Sends help text."""
    if not bot:
        raise ValueError("Bot instance is required for send_help")
    if not keyboard:
        keyboard = await paginate_modules(0, HELPABLE, "help", bot)
    try:
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard,
        )
    except TelegramError as e:
        LOGGER.error("Error sending help message: %s", e)



async def test(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Tests the bot."""
    if update.effective_message:
        await update.effective_message.reply_text(
            "Hola tester! _I_ *have* `markdown`", parse_mode=ParseMode.MARKDOWN
        )
        print(update.effective_message)



async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Starts the bot."""
    bot = context.bot
    if update.effective_chat.type == "private":
        if context.args and len(context.args) >= 1:
            if context.args[0].lower() == "help":
                await send_help(update.effective_chat.id, HELP_STRINGS, bot=bot)

            elif context.args[0].lower().startswith("stngs_"):
                match = re.match("stngs_(.*)", context.args[0].lower())
                if match:
                    chat_id_to_get = match.group(1)
                    chat = await bot.get_chat(chat_id_to_get)
                    user_id = update.effective_user.id
                    is_admin = await is_user_admin(chat, user_id)
                    if is_admin:
                        await send_settings(chat_id_to_get, user_id, False, bot=bot)
                    else:
                        await send_settings(chat_id_to_get, user_id, True, bot=bot)

            elif context.args[0][1:].isdigit() and "rules" in IMPORTED:
                # from tg_bot.modules.rules import send_rules  # Import inside the condition
                # await IMPORTED["rules"].send_rules(update, context.args[0], from_pm=True)
                if "rules" in IMPORTED:
                    rules_module = IMPORTED["rules"]
                    if hasattr(rules_module, "send_rules"):
                        await rules_module.send_rules(update, context.args[0], from_pm=True)
                    else:
                        LOGGER.warning("rules module does not have send_rules function.")
                else:
                    LOGGER.warning("rules module not loaded")

        else:
            first_name = update.effective_user.first_name
            await update.effective_message.reply_text(
                PM_START_TEXT.format(
                    escape_markdown(first_name),
                    escape_markdown(bot.first_name),
                    OWNER_ID,
                ),
                parse_mode=ParseMode.MARKDOWN,
            )
    else:
        await update.effective_message.reply_text("Yo, whadup?")



async def error_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Error handler."""
    error = context.error
    try:
        raise error
    except Unauthorized:
        LOGGER.error("Unauthorized: %s", error)
        # Remove chat ID from conversation list
    except BadRequest:
        LOGGER.error("BadRequest: %s", error)
        # Handle malformed requests
    except TimedOut:
        LOGGER.error("TimedOut: %s", error)
        # Handle slow connection problems
    except NetworkError:
        LOGGER.error("NetworkError: %s", error)
        # Handle other connection problems
    except ChatMigrated as err:
        LOGGER.error("ChatMigrated: %s", err)
        # Handle chat migration
    except TelegramError:
        LOGGER.error("TelegramError: %s", error)
        # Handle other Telegram errors
    except Exception as e:
        LOGGER.exception("Exception in error_callback: %s, update: %s", e, update)



async def help_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Help button handler."""
    query = update.callback_query
    if not query:
        return  # Make sure there is a query
    bot = context.bot

    mod_match = re.match(r"help_module\((.+?)\)", query.data)
    prev_match = re.match(r"help_prev\((.+?)\)", query.data)
    next_match = re.match(r"help_next\((.+?)\)", query.data)
    back_match = re.match(r"help_back", query.data)

    try:
        if mod_match:
            module = mod_match.group(1)
            if module in HELPABLE:
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
                HELP_STRINGS.format(bot.first_name),  # Pass bot name
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=await paginate_modules(
                    curr_page - 1, HELPABLE, "help", bot
                ),
            )
        elif next_match:
            next_page = int(next_match.group(1))
            await query.message.reply_text(
                HELP_STRINGS.format(bot.first_name),  # Pass bot name
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=await paginate_modules(
                    next_page + 1, HELPABLE, "help", bot
                ),
            )
        elif back_match:
            await query.message.reply_text(
                text=HELP_STRINGS.format(bot.first_name),  # Pass bot name here
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=await paginate_modules(0, HELPABLE, "help", bot),
            )

        # Ensure no spinny white circle
        await query.answer()
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
    """Gets help."""
    chat = update.effective_chat  # type: Optional[Chat]
    args = context.args
    bot = context.bot

    # ONLY send help in PM
    if chat.type != Chat.PRIVATE:
        await update.effective_message.reply_text(
            "Contact me in PM to get the list of possible commands.",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            text="Help",
                            url=f"t.me/{bot.username}?start=help",
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
            InlineKeyboardMarkup(
                [[InlineKeyboardButton(text="Back", callback_data="help_back")]]
            ),
            bot=bot,
        )

    else:
        await send_help(chat.id, HELP_STRINGS.format(bot.first_name), bot=bot)  # Pass bot



async def send_settings(chat_id: Union[int, str], user_id: int, user=False, bot: Bot = None) -> None:
    """Sends settings."""
    if not bot:
        raise ValueError("Bot instance is required for send_settings")

    if user:
        if USER_SETTINGS:
            settings = "\n\n".join(
                "*{}*:\n{}".format(mod.__mod_name__, await mod.__user_settings__(user_id))
                for mod in USER_SETTINGS.values()
            )
            try:
                await bot.send_message(
                    user_id,
                    "These are your current settings:" + "\n\n" + settings,
                    parse_mode=ParseMode.MARKDOWN,
                )
            except TelegramError as e:
                LOGGER.error(f"Error sending user settings: {e}")

        else:
            try:
                await bot.send_message(
                    user_id,
                    "Seems like there aren't any user specific settings available :'(",
                    parse_mode=ParseMode.MARKDOWN,
                )
            except TelegramError as e:
                LOGGER.error(f"Error sending no user settings message: {e}")
    else:
        if CHAT_SETTINGS:
            chat_name = (await bot.get_chat(chat_id)).title
            try:
                await bot.send_message(
                    user_id,
                    text="Which module would you like to check {}'s settings for?".format(
                        chat_name
                    ),
                    reply_markup=await paginate_modules(
                        0, CHAT_SETTINGS, "stngs", chat=chat_id, bot=bot
                    ),
                )
            except TelegramError as e:
                LOGGER.error(f"Error sending module settings message: {e}")
        else:
            try:
                await bot.send_message(
                    user_id,
                    "Seems like there aren't any chat settings available :'(\nSend this "
                    "in a group chat you're admin in to find its current settings!",
                    parse_mode=ParseMode.MARKDOWN,
                )
            except TelegramError as e:
                LOGGER.error(f"Error sending no chat settings message: {e}")



async def settings_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Settings button handler."""
    query = update.callback_query
    if not query:
        return
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
                escape_markdown(CHAT_SETTINGS[module].__mod_name__),
            ) + await CHAT_SETTINGS[module].__chat_settings__(chat_id, user.id)
            await query.message.reply_text(
                text=text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                text="Back",
                                callback_data="stngs_back({})".format(chat_id),
                            )
                        ]
                    ]
                ),
            )

        elif prev_match:
            chat_id = prev_match.group(1)
            curr_page = int(prev_match.group(2))
            chat = await bot.get_chat(chat_id)
            await query.message.reply_text(
                "Hi there! There are quite a few settings for {} - go ahead and pick what "
                "you're interested in.".format(chat.title),
                reply_markup=await paginate_modules(
                    curr_page - 1, CHAT_SETTINGS, "stngs", chat=chat_id, bot=bot
                ),
            )

        elif next_match:
            chat_id = next_match.group(1)
            next_page = int(next_match.group(2))
            chat = await bot.get_chat(chat_id)
            await query.message.reply_text(
                "Hi there! There are quite a few settings for {} - go ahead and pick what "
                "you're interested in.".format(chat.title),
                reply_markup=await paginate_modules(
                    next_page + 1, CHAT_SETTINGS, "stngs", chat=chat_id, bot=bot
                ),
            )

        elif back_match:
            chat_id = back_match.group(1)
            chat = await bot.get_chat(chat_id)
            await query.message.reply_text(
                text="Hi there! There are quite a few settings for {} - go ahead and pick what "
                "you're interested in.".format(escape_markdown(chat.title)),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=await paginate_modules(
                    0, CHAT_SETTINGS, "stngs", chat=chat_id, bot=bot
                ),
            )

        # Ensure no spinny white circle
        await query.answer()
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
    """Gets settings."""
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    msg = update.effective_message  # type: Optional[Message]
    args = context.args
    bot = context.bot

    # ONLY send settings in PM
    if chat.type != Chat.PRIVATE:
        if await is_user_admin(chat, user.id):
            text = "Click here to get this chat's settings, as well as yours."
            await msg.reply_text(
                text,
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                text="Settings",
                                url=f"t.me/{bot.username}?start=stngs_{chat.id}",
                            )
                        ]
                    ]
                ),
            )
        else:
            text = "Click here to check your settings."
            await msg.reply_text(
                text,
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                text="Settings",
                                url=f"t.me/{bot.username}?start=stngs_{chat.id}",
                            )
                        ]
                    ]
                ),
            )

    else:
        await send_settings(chat.id, user.id, True, bot=bot)



async def donate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles donations."""
    user = update.effective_message.from_user
    chat = update.effective_chat  # type: Optional[Chat]
    bot = context.bot

    if chat.type == Chat.PRIVATE:
        await update.effective_message.reply_text(
            DONATE_STRING, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True
        )

        if OWNER_ID != 254318997 and DONATION_LINK:
            await update.effective_message.reply_text(
                "You can also donate to the person currently running me "
                "[here]({})".format(DONATION_LINK),
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True,
            )

    else:
        try:
            await bot.send_message(
                user.id,
                DONATE_STRING,
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True,
            )
            await update.effective_message.reply_text(
                "I've PM'ed you about donating to my creator!"
            )
        except Unauthorized:
            await update.effective_message.reply_text(
                "Contact me in PM first to get donation information."
            )



async def migrate_chats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Migrates chats."""
    msg = update.effective_message  # type: Optional[Message]
    if msg is None:
        return

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
        await mod.__migrate__(old_chat, new_chat)  # Await the migrate function

    LOGGER.info("Successfully migrated!")
    # raise DispatcherHandlerStop  # Not needed in PTB 20



async def post_init(app: Application) -> None:
    """Post initialization hook."""
    await load_modules()
    # bot = app.bot # Not used.
    if WEBHOOK:
        LOGGER.info("Using Webhooks")
        await app.bot.set_webhook(url=URL + TOKEN)
    else:
        LOGGER.info("Using Long Polling")
    # any other post init tasks



async def main() -> None:
    """Main function."""
    # Create the Application and pass it your bot's token.
    application = (
        Application.builder().token(TOKEN).post_init(post_init).build()
    )  # Corrected
    # application = Application.builder().token(TOKEN).build() # simplified

    # Register handlers
    application.add_handler(CommandHandler("test", test))
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", get_help))
    application.add_handler(CallbackQueryHandler(help_button, pattern=r"help_"))
    application.add_handler(CommandHandler("settings", get_settings))
    application.add_handler(
        CallbackQueryHandler(settings_button, pattern=r"stngs_")
    )
    application.add_handler(MessageHandler(filters.ChatMigrated(), migrate_chats))
    application.add_handler(CommandHandler("donate", donate))

    # Error handler
    application.add_error_handler(error_callback)

    # Run the app
    if WEBHOOK:
        # Set up webhook
        await application.bot.set_webhook(url=URL + TOKEN,
                                          certificate=open(CERT_PATH, "rb") if CERT_PATH else None)
        # Start the server
        await application.start_webhook(listen="0.0.0.0", port=PORT, webhook_url=URL + TOKEN)
    else:
        # Start long polling
        await application.run_polling(allowed_updates=Update.ALL_TYPES)



# CHATS_CNT = {}  # Removed global variables
# CHATS_TIME = {}  # These should be in a middleware, not global

async def antiflood(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Antiflood middleware."""
    chat_id = update.effective_chat.id
    now = datetime.datetime.utcnow()

    if "CHATS_CNT" not in context.application.chat_data:
        context.application.chat_data["CHATS_CNT"] = {}
    if "CHATS_TIME" not in context.application.chat_data:
        context.application.chat_data["CHATS_TIME"] = {}

    cnt = context.application.chat_data["CHATS_CNT"].get(chat_id, 0)
    t = context.application.chat_data["CHATS_TIME"].get(
        chat_id, datetime.datetime(1970, 1, 1)
    )

    if now > t + datetime.timedelta(0, 1):
        context.application.chat_data["CHATS_TIME"][chat_id] = now
        cnt = 0
    else:
        cnt += 1

    if cnt > 10:
        return  # Drop the update
    context.application.chat_data["CHATS_CNT"][chat_id] = cnt
    return None # Continue processing


async def paginate_modules(
    page_n: int,
    mod_dict: dict,
    prefix: str,
    chat: Union[int, str] = None,
    bot: Bot = None,
) -> InlineKeyboardMarkup:
    """Paginates modules."""
    if not bot:
        raise ValueError("Bot instance is required for paginate_modules")
    items_per_page = 5
    modules = sorted(mod_dict.items())
    lower_bound = page_n * items_per_page
    upper_bound = min((page_n + 1) * items_per_page, len(modules))
    relevant_modules = dict(modules[lower_bound:upper_bound])

    buttons = [
        InlineKeyboardButton(
            text=f"{mod[1].__mod_name__}",
            callback_data=f"{prefix}_module({chat},{mod_name})"
            if chat
            else f"{prefix}_module({mod_name})",
        )
        for mod_name, mod in relevant_modules.items()
    ]
    rows = [buttons[i : i + 1] for i in range(0, len(buttons), 1)]  # one button per row

    if page_n > 0:
        prev_page = InlineKeyboardButton(
            text="Previous", callback_data=f"{prefix}_prev({chat},{page_n})"
        ) if chat else InlineKeyboardButton(
            text="Previous", callback_data=f"{prefix}_prev({page_n})"
        )
        rows.append([prev_page])
    if upper_bound < len(modules):
        next_page = InlineKeyboardButton(
            text="Next", callback_data=f"{prefix}_next({chat},{page_n})"
        ) if chat else InlineKeyboardButton(
            text="Next", callback_data=f"{prefix}_next({page_n})"
        )
        if page_n > 0:
            rows[-1].append(next_page)
        else:
            rows.append([next_page])
    rows.append([InlineKeyboardButton(text="Back", callback_data=f"{prefix}_back({chat})")]) if chat else rows.append([InlineKeyboardButton(text="Back", callback_data=f"{prefix}_back")])
    return InlineKeyboardMarkup(rows)



if __name__ == "__main__":
    # asyncio.run(main()) # Use this
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped.")
