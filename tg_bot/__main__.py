import datetime
import importlib
import re
from typing import Optional, List, Dict, Tuple, Union

from telegram import Update, Bot, User, Chat
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
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    Application,
    ConversationHandler,
    ContextTypes,
)
from telegram.utils.helpers import escape_markdown

# Needed to dynamically load modules
# NOTE: Module order is not guaranteed, specify that in the config file!
from tg_bot import dispatcher, updater, TOKEN, WEBHOOK, OWNER_ID, DONATION_LINK, CERT_PATH, PORT, URL, LOGGER, ALLOW_EXCL
from tg_bot.modules import ALL_MODULES
from tg_bot.modules.helper_funcs.chat_status import is_user_admin
from tg_bot.modules.helper_funcs.misc import paginate_modules

# Moved here to avoid potential issues with undefined variables.
PM_START_TEXT = """
Hi {}, my name is {}! If you have any questions on how to use me, read /help - and then head to @MarieSupport.

I'm a group manager bot built in python3, using the python-telegram-bot library, and am fully opensource;
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
""".format(dispatcher.bot.first_name, "" if not ALLOW_EXCL else "\nAll commands can either be used with / or !.\n")

DONATE_STRING = """Heya, glad to hear you want to donate!
It took lots of work for my creator to get me to where I am now, and every donation helps
motivate him to make me even better. All the donation money will go to a better VPS to host me, and/or beer
(see his bio!). He's just a poor student, so every little helps!
There are two ways of paying him; [PayPal](paypal.me/PaulSonOfLars), or [Monzo](monzo.me/paulnionvestergaardlarsen)."""

IMPORTED: Dict[str, object] = {}
MIGRATEABLE: List[object] = []
HELPABLE: Dict[str, object] = {}
STATS: List[object] = []
USER_INFO: List[object] = []
DATA_IMPORT: List[object] = []
DATA_EXPORT: List[object] = []

CHAT_SETTINGS: Dict[str, object] = {}
USER_SETTINGS: Dict[str, object] = {}

GDPR: List[object] = []
# Ensure application is defined.
application = dispatcher.application


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error and send a telegram message to notify the developer."""
    # This traceback is created with a limit_value that may be too small.
    # Even when a large enough limit_value is passed to the traceback.format_exception,
    # the generated traceback can have newlines missing.
    # LOGGER.error(msg="Exception while handling an update:", exc_info=context.error)
    LOGGER.exception("Exception while handling an update")

    # Without escape_markdown, the user could be tricked into tapping bad links.
    # The context.error is already a string, so we don't need to convert it.
    message = (
        "An error occurred while handling the update.\n"
        f"<pre>{escape_markdown(str(context.error))}</pre>"
    )
    # Sends error to the user
    if update:
        await context.bot.send_message(
            chat_id=update.effective_chat.id, text=message, parse_mode=ParseMode.HTML
        )
    # Sends error to the developer
    await context.bot.send_message(
        chat_id=OWNER_ID, text=message, parse_mode=ParseMode.HTML
    )
    # Log the error
    LOGGER.error(f"Error: {context.error}")



for module_name in ALL_MODULES:
    try:
        imported_module = importlib.import_module("tg_bot.modules." + module_name)
        if not hasattr(imported_module, "__mod_name__"):
            imported_module.__mod_name__ = imported_module.__name__

        if not imported_module.__mod_name__.lower() in IMPORTED:
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
    except ImportError as exc:
        LOGGER.warning("Can't import module %s, due to error %s", module_name, exc)


async def send_help(chat_id: int, text: str, keyboard: Optional[InlineKeyboardMarkup] = None) -> None:
    """Sends help text to the chat.

    Args:
        chat_id: The ID of the chat to send the help message to.
        text: The help text to send.
        keyboard: Optional inline keyboard markup to include.
    """
    if not keyboard:
        keyboard = InlineKeyboardMarkup(paginate_modules(0, HELPABLE, "help"))
    try:
        await application.bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard,
        )
    except TelegramError as e:
        LOGGER.exception("Error sending help message: %s", e)



async def test(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Tests the bot's functionality."""
    if update.effective_message:
        await update.effective_message.reply_text(
            "Hola tester! _I_ *have* `markdown`", parse_mode=ParseMode.MARKDOWN
        )
        print(update.effective_message)



async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /start command.

    Args:
        update: The incoming update.
        context: The context object.
    """
    if update.effective_chat.type == "private":
        if context.args and len(context.args) >= 1:
            if context.args[0].lower() == "help":
                await send_help(update.effective_chat.id, HELP_STRINGS)
                return  # Added return

            elif context.args[0].lower().startswith("stngs_"):
                match = re.match(r"stngs_(.*)", context.args[0].lower())
                if match:  # Added check to ensure match is not None
                    chat_id_str = match.group(1)
                    try:
                        chat_id = int(chat_id_str)
                        chat = await application.bot.get_chat(chat_id)
                        user_id = update.effective_user.id
                        if await is_user_admin(chat, user_id):
                            await send_settings(chat_id, user_id, False, context)
                        else:
                            await send_settings(chat_id, user_id, True, context)
                    except ValueError:
                        LOGGER.warning(f"Invalid chat ID: {chat_id_str}")
                return  # Added return

            elif context.args[0][1:].isdigit() and "rules" in IMPORTED:
                # Assuming IMPORTED["rules"] has a send_rules function.
                if hasattr(IMPORTED["rules"], "send_rules"):
                  await IMPORTED["rules"].send_rules(update, context.args[0], from_pm=True)
                return # Added return
        first_name = update.effective_user.first_name
        await update.effective_message.reply_text(
            PM_START_TEXT.format(
                escape_markdown(first_name),
                escape_markdown(application.bot.first_name),
                OWNER_ID,
            ),
            parse_mode=ParseMode.MARKDOWN,
        )
    else:
        await update.effective_message.reply_text("Yo, whadup?")



async def help_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles inline keyboard button presses for help."""
    query = update.callback_query
    if not query:
        return

    mod_match = re.match(r"help_module\((.+?)\)", query.data)
    prev_match = re.match(r"help_prev\((.+?)\)", query.data)
    next_match = re.match(r"help_next\((.+?)\)", query.data)
    back_match = re.match(r"help_back", query.data)

    try:
        if mod_match:
            module = mod_match.group(1)
            if module in HELPABLE:
                text = f"Here is the help for the *{HELPABLE[module].__mod_name__}* module:\n{HELPABLE[module].__help__}"
                await query.message.reply_text(
                    text=text,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=InlineKeyboardMarkup(
                        [[InlineKeyboardButton(text="Back", callback_data="help_back")]]
                    ),
                )
            else:
                await query.answer(text="Module not found.")

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
    """Handles the /help command.  Sends help text, possibly for a specific module."""
    chat = update.effective_chat  # type: Optional[Chat]
    args = context.args

    # ONLY send help in PM
    if chat.type != chat.PRIVATE:
        await update.effective_message.reply_text(
            "Contact me in PM to get the list of possible commands.",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            text="Help",
                            url=f"t.me/{application.bot.username}?start=help",
                        )
                    ]
                ]
            ),
        )
        return

    elif args and len(args) >= 1 and any(args[0].lower() == x for x in HELPABLE):
        module = args[0].lower()
        text = (
            f"Here is the available help for the *{HELPABLE[module].__mod_name__}* module:\n"
            f"{HELPABLE[module].__help__}"
        )
        await send_help(
            chat.id,
            text,
            InlineKeyboardMarkup([[InlineKeyboardButton(text="Back", callback_data="help_back")]]),
        )

    else:
        await send_help(chat.id, HELP_STRINGS)



async def send_settings(chat_id: int, user_id: int, user: bool = False, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends the settings for a chat or a user.

    Args:
        chat_id: The ID of the chat.
        user_id: The ID of the user.
        user: Whether to send user-specific settings.
        context:  The context object.
    """
    if user:
        if USER_SETTINGS:
            settings = "\n\n".join(
                f"*{mod.__mod_name__}*:\n{mod.__user_settings__(user_id)}"
                for mod in USER_SETTINGS.values()
            )
            await context.bot.send_message(
                user_id,
                "These are your current settings:" + "\n\n" + settings,
                parse_mode=ParseMode.MARKDOWN,
            )
        else:
            await context.bot.send_message(
                user_id,
                "Seems like there aren't any user-specific settings available :'(",
                parse_mode=ParseMode.MARKDOWN,
            )
    else:
        if CHAT_SETTINGS:
            chat_name = (await context.bot.get_chat(chat_id)).title
            await context.bot.send_message(
                user_id,
                text=f"Which module would you like to check {chat_name}'s settings for?",
                reply_markup=InlineKeyboardMarkup(
                    paginate_modules(0, CHAT_SETTINGS, "stngs", chat=chat_id)
                ),
            )
        else:
            await context.bot.send_message(
                user_id,
                "Seems like there aren't any chat settings available :'(\nSend this "
                "in a group chat you're admin in to find its current settings!",
                parse_mode=ParseMode.MARKDOWN,
            )



async def settings_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles inline keyboard button presses for settings."""
    query = update.callback_query
    if not query:
      return

    user = update.effective_user
    mod_match = re.match(r"stngs_module\((.+?),(.+?)\)", query.data)
    prev_match = re.match(r"stngs_prev\((.+?),(.+?)\)", query.data)
    next_match = re.match(r"stngs_next\((.+?),(.+?)\)", query.data)
    back_match = re.match(r"stngs_back\((.+?)\)", query.data)

    try:
        if mod_match:
            chat_id = mod_match.group(1)
            module = mod_match.group(2)
            chat = await context.bot.get_chat(int(chat_id))
            text = (
                f"*{escape_markdown(chat.title)}* has the following settings for the "
                f"*{CHAT_SETTINGS[module].__mod_name__}* module:\n\n"
                f"{CHAT_SETTINGS[module].__chat_settings__(int(chat_id), user.id)}"
            )
            await query.message.reply_text(
                text=text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                text="Back", callback_data=f"stngs_back({chat_id})"
                            )
                        ]
                    ]
                ),
            )

        elif prev_match:
            chat_id = prev_match.group(1)
            curr_page = int(prev_match.group(2))
            chat = await context.bot.get_chat(int(chat_id))
            await query.message.reply_text(
                f"Hi there! There are quite a few settings for {chat.title} - go ahead and pick what "
                "you're interested in.",
                reply_markup=InlineKeyboardMarkup(
                    paginate_modules(curr_page - 1, CHAT_SETTINGS, "stngs", chat=int(chat_id))
                ),
            )

        elif next_match:
            chat_id = next_match.group(1)
            next_page = int(next_match.group(2))
            chat = await context.bot.get_chat(int(chat_id))
            await query.message.reply_text(
                f"Hi there! There are quite a few settings for {chat.title} - go ahead and pick what "
                "you're interested in.",
                reply_markup=InlineKeyboardMarkup(
                    paginate_modules(next_page + 1, CHAT_SETTINGS, "stngs", chat=int(chat_id))
                ),
            )

        elif back_match:
            chat_id = back_match.group(1)
            chat = await context.bot.get_chat(int(chat_id))
            await query.message.reply_text(
                text=f"Hi there! There are quite a few settings for {escape_markdown(chat.title)} - go ahead and pick what "
                "you're interested in.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(
                    paginate_modules(0, CHAT_SETTINGS, "stngs", chat=int(chat_id))
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
    """Handles the /settings command.  Sends settings, either for the chat or the user."""
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    msg = update.effective_message  # type: Optional[Message]

    # ONLY send settings in PM
    if chat.type != chat.PRIVATE:
        if await is_user_admin(chat, user.id):
            text = "Click here to get this chat's settings, as well as yours."
            await msg.reply_text(
                text,
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                text="Settings",
                                url=f"t.me/{application.bot.username}?start=stngs_{chat.id}",
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
                                url=f"t.me/{application.bot.username}?start=stngs_{user.id}",
                            )
                        ]
                    ]
                ),
            )

    else:
        await send_settings(chat.id, user.id, True, context)



async def donate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /donate command.  Sends donation information."""
    user = update.effective_message.from_user
    chat = update.effective_chat  # type: Optional[Chat]

    if chat.type == "private":
        await update.effective_message.reply_text(
            DONATE_STRING, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True
        )

        if OWNER_ID != 254318997 and DONATION_LINK:
            await update.effective_message.reply_text(
                "You can also donate to the person currently running me "
                f"[here]({DONATION_LINK})",
                parse_mode=ParseMode.MARKDOWN,
            )

    else:
        try:
            await context.bot.send_message(
                user.id, DONATE_STRING, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True
            )
            await update.effective_message.reply_text("I've PM'ed you about donating to my creator!")
        except Unauthorized:
            await update.effective_message.reply_text("Contact me in PM first to get donation information.")



async def migrate_chats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles chat migrations."""
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
        if hasattr(mod, "__migrate__"):
          await mod.__migrate__(old_chat, new_chat)

    LOGGER.info("Successfully migrated!")
    raise ConversationHandler.END


# CHATS_CNT: Dict[int, int] = {} # Removed global variable
# CHATS_TIME: Dict[int, datetime.datetime] = {} # Removed global variable


async def process_update(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Processes incoming updates, handling flood control and errors."""
    # An error happened while polling
    if isinstance(update, TelegramError):
        await error_handler(update, context)
        return

    now = datetime.datetime.utcnow()
    chat_id = update.effective_chat.id
    # Use chat_data for persistence
    cnt = context.chat_data.get("CHATS_CNT", 0)
    t = context.chat_data.get("CHATS_TIME", datetime.datetime(1970, 1, 1))

    if now > t + datetime.timedelta(0, 1):
        context.chat_data["CHATS_TIME"] = now
        cnt = 0
    else:
        cnt += 1

    if cnt > 10:
        return

    context.chat_data["CHATS_CNT"] = cnt
    # print(f"Handlers are {application.handlers}") # For Debug
    if application.handlers and application.handlers.get(0):
      for group in application.handlers.get(0): # changed from application.groups to application.handlers[0]
          try:
              if group and group.check_update(update):
                  await group.handle_update(update, context)
                  #   break # Removed break
          except ConversationHandler.End:
              LOGGER.debug('Stopping further handlers due to ConversationHandler.End')
              return
          except TelegramError as te:
              LOGGER.warning('A TelegramError was raised while processing the Update')
              await error_handler(update, context)
              return
          except Exception:
              LOGGER.exception('An uncaught error was raised while processing the update')



def main() -> None:
    """Main function to start the bot."""
    # Handlers
    test_handler = CommandHandler("test", test)
    start_handler = CommandHandler("start", start)
    help_handler = CommandHandler("help", get_help)
    help_callback_handler = CallbackQueryHandler(help_button, pattern=r"help_")
    settings_handler = CommandHandler("settings", get_settings)
    settings_callback_handler = CallbackQueryHandler(settings_button, pattern=r"stngs_")
    donate_handler = CommandHandler("donate", donate)
    migrate_handler = MessageHandler(
        callback=migrate_chats, filters=telegram.ext.filters.ChatMigrationUpdated()
    )

    # Add handlers to the application
    application.add_handler(test_handler)
    application.add_handler(start_handler)
    application.add_handler(help_handler)
    application.add_handler(help_callback_handler)
    application.add_handler(settings_handler)
    application.add_handler(settings_callback_handler)
    application.add_handler(migrate_handler)
    application.add_handler(donate_handler)
    # application.add_error_handler(error_handler) # Removed error handler, now using the one defined at the top

    # Set process_update as the default update processor.  This is necessary for
    #  handling flood control.
    application.process_update = process_update  # type: ignore[method-assign] # Assign the function

    # Start the bot
    if WEBHOOK:
        LOGGER.info("Using webhooks.")
        application.run_webhook(
            listen="127.0.0.1",
            port=PORT,
            webhook_url=URL + TOKEN,
            cert=CERT_PATH if CERT_PATH else None,
        )
    else:
        LOGGER.info("Using long polling.")
        application.run_polling(timeout=15, read_timeout=20) # Read timeout added
    # application.run_polling(allowed_updates=Update.ALL, timeout=15, read_latency=4) # Removed read_latency, added allowed_updates


if __name__ == "__main__":
    LOGGER.info("Successfully loaded modules: %s", str(ALL_MODULES))
    main()
