import datetime
import importlib
import re
from typing import Optional, List, Dict, Any

from telegram import Message, Chat, Update, Bot, User
from telegram import ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.error import (
    Unauthorized,
    BadRequest,
    TimedOut,
    NetworkError,
    ChatMigrated,
    TelegramError,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from telegram.constants import ParseMode
from telegram.utils.helpers import escape_markdown

from tg_bot import (
    TOKEN,
    WEBHOOK,
    OWNER_ID,
    DONATION_LINK,
    CERT_PATH,
    PORT,
    URL,
    LOGGER,
    ALLOW_EXCL,
    ALL_MODULES,
)
from tg_bot.modules.helper_funcs.chat_status import is_user_admin
from tg_bot.modules.helper_funcs.misc import paginate_modules

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
    "{}", "" if not ALLOW_EXCL else "\nAll commands can either be used with / or !.\n"
)

DONATE_STRING = """Heya, glad to hear you want to donate!
It took lots of work for my creator to get me to where I am now, and every donation helps \
motivate him to make me even better. All the donation money will go to a better VPS to host me, and/or beer \
(see his bio!). He's just a poor student, so every little helps!
There are two ways of paying him; [PayPal](paypal.me/PaulSonOfLars), or [Monzo](monzo.me/paulnionvestergaardlarsen)."""

IMPORTED: Dict[str, Any] = {}
MIGRATEABLE: List[Any] = []
HELPABLE: Dict[str, Any] = {}
STATS: List[Any] = []
USER_INFO: List[Any] = []
DATA_IMPORT: List[Any] = []
DATA_EXPORT: List[Any] = []

CHAT_SETTINGS: Dict[str, Any] = {}
USER_SETTINGS: Dict[str, Any] = {}

GDPR: List[Any] = []

for module_name in ALL_MODULES:
    imported_module = importlib.import_module("tg_bot.modules." + module_name)
    if not hasattr(imported_module, "__mod_name__"):
        imported_module.__mod_name__ = imported_module.__name__

    if imported_module.__mod_name__.lower() not in IMPORTED:
        IMPORTED[imported_module.__mod_name__.lower()] = imported_module
    else:
        raise Exception("Can't have two modules with the same name! Please change one")

    if hasattr(imported_module, "__help__") and imported_module.__help__:
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


async def send_help(chat_id: int, text: str, keyboard: Optional[InlineKeyboardMarkup] = None) -> None:
    """Sends help text to the specified chat_id."""
    if not keyboard:
        keyboard = InlineKeyboardMarkup(paginate_modules(0, HELPABLE, "help"))
    try:
        await application.bot.send_message(
            chat_id=chat_id, text=text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard
        )
    except TelegramError as e:
        LOGGER.error(f"Error sending help to {chat_id}: {e}")


async def test(update: Update, context: Any) -> None:
    """Echo the user message."""
    if update.effective_message:
        await update.effective_message.reply_text("This person edited a message")
        LOGGER.info(f"Test update: {update.effective_message}")


async def start(update: Update, context: Any) -> None:
    """Send a message when the command /start is issued."""
    if update.effective_chat and update.effective_chat.type == "private":
        if context.args and len(context.args) >= 1:
            arg = context.args[0].lower()
            if arg == "help":
                await send_help(update.effective_chat.id, HELP_STRINGS.format(application.bot.first_name))
            elif arg.startswith("stngs_"):
                match = re.match(r"stngs_(.*)", arg)
                if match:
                    chat_id = match.group(1)
                    chat = await application.bot.get_chat(chat_id)
                    user_id = update.effective_user.id
                    if await is_user_admin(chat, user_id):
                        await send_settings(chat_id, user_id, False)
                    else:
                        await send_settings(chat_id, user_id, True)
            elif arg[1:].isdigit() and "rules" in IMPORTED:
                # Assuming rules module has a send_rules function that is now async
                if hasattr(IMPORTED["rules"], "send_rules"):
                    await IMPORTED["rules"].send_rules(update, arg, from_pm=True)
                else:
                    LOGGER.warning("Rules module is missing send_rules function.")
        else:
            first_name = update.effective_user.first_name
            await update.effective_message.reply_text(
                PM_START_TEXT.format(
                    escape_markdown(first_name),
                    escape_markdown(application.bot.first_name),
                    OWNER_ID,
                ),
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True,
            )
    else:
        if update.effective_message:
            await update.effective_message.reply_text("Yo, whadup?")


async def error_handler(update: Optional[Update], context: Any) -> None:
    """Log the error and send a telegram message to notify the developer."""
    LOGGER.error(f"Exception while handling an update: {context.error}")
    # You might want to add more sophisticated error handling here, like sending
    # a message to the owner or logging detailed stack traces.


async def help_button(update: Update, context: Any) -> None:
    """Handles the inline keyboard buttons for help."""
    query = update.callback_query
    if not query:
        return
    await query.answer()  # Acknowledge the callback query

    mod_match = re.match(r"help_module\((.+?)\)", query.data)
    prev_match = re.match(r"help_prev\((.+?)\)", query.data)
    next_match = re.match(r"help_next\((.+?)\)", query.data)
    back_match = re.match(r"help_back", query.data)

    try:
        if mod_match:
            module = mod_match.group(1)
            text = f"Here is the help for the *{HELPABLE[module].__mod_name__}* module:\n" + HELPABLE[module].__help__
            await query.message.reply_text(
                text=text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(text="Back", callback_data="help_back")]]),
            )
        elif prev_match:
            curr_page = int(prev_match.group(1))
            await query.message.edit_text(
                HELP_STRINGS.format(application.bot.first_name),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(paginate_modules(curr_page - 1, HELPABLE, "help")),
            )
        elif next_match:
            next_page = int(next_match.group(1))
            await query.message.edit_text(
                HELP_STRINGS.format(application.bot.first_name),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(paginate_modules(next_page + 1, HELPABLE, "help")),
            )
        elif back_match:
            await query.message.edit_text(
                text=HELP_STRINGS.format(application.bot.first_name),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(paginate_modules(0, HELPABLE, "help")),
            )
        await query.message.delete()
    except BadRequest as excp:
        if excp.message == "Message is not modified":
            pass
        elif excp.message == "Query_id_invalid":
            pass
        elif excp.message == "Message can't be deleted":
            pass
        else:
            LOGGER.exception(f"Exception in help buttons: {query.data} - {excp.message}")


async def get_help(update: Update, context: Any) -> None:
    """Sends the help text to the user."""
    chat = update.effective_chat
    args = context.args

    # ONLY send help in PM
    if chat and chat.type != Chat.PRIVATE:
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton(text="Help", url=f"t.me/{application.bot.username}?start=help")]]
        )
        if update.effective_message:
            await update.effective_message.reply_text(
                "Contact me in PM to get the list of possible commands.", reply_markup=keyboard
            )
        return

    elif args and len(args) >= 1 and args[0].lower() in HELPABLE:
        module = args[0].lower()
        text = f"Here is the available help for the *{HELPABLE[module].__mod_name__}* module:\n" + HELPABLE[module].__help__
        await send_help(chat.id, text, InlineKeyboardMarkup([[InlineKeyboardButton(text="Back", callback_data="help_back")]])
        )
    else:
        await send_help(chat.id, HELP_STRINGS.format(application.bot.first_name))


async def send_settings(chat_id: int, user_id: int, user: bool = False) -> None:
    """Sends the settings for the chat or user."""
    if user:
        if USER_SETTINGS:
            settings = "\n\n".join(
                f"*{mod.__mod_name__}*:\n{await mod.__user_settings__(user_id)}"
                for mod in USER_SETTINGS.values()
                if hasattr(mod, "__user_settings__")
            )
            await application.bot.send_message(
                user_id, "These are your current settings:" + "\n\n" + settings, parse_mode=ParseMode.MARKDOWN
            )
        else:
            await application.bot.send_message(
                user_id,
                "Seems like there aren't any user specific settings available :'(",
                parse_mode=ParseMode.MARKDOWN,
            )
    else:
        if CHAT_SETTINGS:
            chat = await application.bot.get_chat(chat_id)
            await application.bot.send_message(
                user_id,
                text=f"Which module would you like to check {escape_markdown(chat.title)}'s settings for?",
                reply_markup=InlineKeyboardMarkup(paginate_modules(0, CHAT_SETTINGS, "stngs", chat=chat_id)),
            )
        else:
            await application.bot.send_message(
                user_id,
                "Seems like there aren't any chat settings available :'(\nSend this "
                "in a group chat you're admin in to find its current settings!",
                parse_mode=ParseMode.MARKDOWN,
            )


async def settings_button(update: Update, context: Any) -> None:
    """Handles the inline keyboard buttons for settings."""
    query = update.callback_query
    user = update.effective_user
    if not query:
        return
    await query.answer()

    mod_match = re.match(r"stngs_module\((.+?),(.+?)\)", query.data)
    prev_match = re.match(r"stngs_prev\((.+?),(.+?)\)", query.data)
    next_match = re.match(r"stngs_next\((.+?),(.+?)\)", query.data)
    back_match = re.match(r"stngs_back\((.+?)\)", query.data)

    try:
        if mod_match:
            chat_id = mod_match.group(1)
            module = mod_match.group(2)
            chat = await application.bot.get_chat(chat_id)
            if module in CHAT_SETTINGS and hasattr(CHAT_SETTINGS[module], "__chat_settings__"):
                settings_text = await CHAT_SETTINGS[module].__chat_settings__(chat_id, user.id)
                text = f"*{escape_markdown(chat.title)}* has the following settings for the *{CHAT_SETTINGS[module].__mod_name__}* module:\n\n{settings_text}"
                await query.message.reply_text(
                    text=text,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=InlineKeyboardMarkup(
                        [[InlineKeyboardButton(text="Back", callback_data=f"stngs_back({chat_id})")]]
                    ),
                )
            else:
                await query.message.reply_text("This module does not have chat settings.")
        elif prev_match:
            chat_id = prev_match.group(1)
            curr_page = int(prev_match.group(2))
            chat = await application.bot.get_chat(chat_id)
            await query.message.edit_text(
                f"Hi there! There are quite a few settings for {escape_markdown(chat.title)} - go ahead and pick what you're interested in.",
                reply_markup=InlineKeyboardMarkup(paginate_modules(curr_page - 1, CHAT_SETTINGS, "stngs", chat=chat_id)),
            )
        elif next_match:
            chat_id = next_match.group(1)
            next_page = int(next_match.group(2))
            chat = await application.bot.get_chat(chat_id)
            await query.message.edit_text(
                f"Hi there! There are quite a few settings for {escape_markdown(chat.title)} - go ahead and pick what 
