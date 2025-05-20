from math import ceil
from typing import List, Dict, Optional, Sequence, Union

from telegram import (
    MAX_MESSAGE_LENGTH,
    InlineKeyboardButton,
    Bot,
    ParseMode,
    User,
    Chat,
)
from telegram.error import TelegramError
from telegram.ext import ExtBot

from tg_bot import LOAD, NO_LOAD

# Use a type alias for better readability
ListOfLists = List[List[InlineKeyboardButton]]


class EqInlineKeyboardButton(InlineKeyboardButton):
    """
    Enhanced InlineKeyboardButton with equality and comparison based on text.
    """

    def __eq__(self, other: object) -> bool:
        """Compare buttons based on their text."""
        if not isinstance(other, InlineKeyboardButton):
            return False
        return self.text == other.text

    def __lt__(self, other: "EqInlineKeyboardButton") -> bool:
        """Compare buttons lexicographically based on their text."""
        return self.text < other.text

    def __gt__(self, other: "EqInlineKeyboardButton") -> bool:
        """Compare buttons lexicographically based on their text."""
        return self.text > other.text

    def __hash__(self) -> int:
        """Make the object hashable."""
        return hash(self.text)



def split_message(msg: str) -> List[str]:
    """
    Split a message into smaller chunks if it exceeds MAX_MESSAGE_LENGTH.

    Args:
        msg: The message string to split.

    Returns:
        A list of message chunks, each within the allowed length.
    """
    if len(msg) <= MAX_MESSAGE_LENGTH:
        return [msg]

    lines = msg.splitlines(True)
    small_msg = ""
    result: List[str] = []
    for line in lines:
        if len(small_msg) + len(line) <= MAX_MESSAGE_LENGTH:
            small_msg += line
        else:
            result.append(small_msg)
            small_msg = line
    else:
        # Append the leftover string.
        result.append(small_msg)
    return result



def paginate_modules(
    page_n: int, module_dict: Dict, prefix: str, chat: Optional[Chat] = None
) -> ListOfLists:
    """
    Paginate a dictionary of modules into a list of InlineKeyboardButton rows.

    Args:
        page_n: The current page number (0-indexed).
        module_dict: A dictionary of modules, where keys are module names
            and values are module objects with a `__mod_name__` attribute.
        prefix: A string prefix for the callback data of the buttons.
        chat:  The chat object.

    Returns:
        A list of button rows, suitable for use in a reply markup.
    """
    if not chat:
        modules = sorted(
            [
                EqInlineKeyboardButton(
                    x.__mod_name__,
                    callback_data="{}_module({})".format(prefix, x.__mod_name__.lower()),
                )
                for x in module_dict.values()
            ]
        )
    else:
        modules = sorted(
            [
                EqInlineKeyboardButton(
                    x.__mod_name__,
                    callback_data="{}_module({},{})".format(
                        prefix, chat.id, x.__mod_name__.lower()
                    ),
                )
                for x in module_dict.values()
            ]
        )

    pairs = list(zip(modules[::2], modules[1::2]))

    if len(modules) % 2 == 1:
        pairs.append((modules[-1],))

    max_num_pages = ceil(len(pairs) / 7)
    modulo_page = page_n % max_num_pages

    # can only have a certain amount of buttons side by side
    if len(pairs) > 7:
        pairs = pairs[modulo_page * 7 : 7 * (modulo_page + 1)] + [
            (
                EqInlineKeyboardButton("<", callback_data="{}_prev({})".format(prefix, modulo_page)),
                EqInlineKeyboardButton(">", callback_data="{}_next({})".format(prefix, modulo_page)),
            )
        ]
    return pairs



def send_to_list(
    bot: Bot,  # Changed from ExtBot to Bot
    send_to: List[int],
    message: str,
    markdown: bool = False,
    html: bool = False,
) -> None:
    """
    Send a message to multiple users.

    Args:
        bot: The Telegram Bot instance.
        send_to: A list of user IDs to send the message to.
        message: The message string to send.
        markdown: Whether to parse the message as Markdown.
        html: Whether to parse the message as HTML.

    Raises:
        Exception: If both markdown and html are True.
    """
    if html and markdown:
        raise Exception("Can only send with either markdown or HTML!")
    for user_id in set(send_to):
        try:
            if markdown:
                bot.send_message(user_id, message, parse_mode=ParseMode.MARKDOWN)
            elif html:
                bot.send_message(user_id, message, parse_mode=ParseMode.HTML)
            else:
                bot.send_message(user_id, message)
        except TelegramError:
            pass  # ignore users who fail




def build_keyboard(buttons: List[InlineKeyboardButton]) -> ListOfLists:
    """
    Build a keyboard (list of lists) from a list of InlineKeyboardButton.

    This function assumes that the buttons have a `same_line` attribute.

    Args:
      buttons: A list of InlineKeyboardButton

    Returns:
      A list of lists of InlineKeyboardButton.
    """
    keyb: ListOfLists = []
    for btn in buttons:
        if hasattr(btn, "same_line") and btn.same_line and keyb:
            keyb[-1].append(btn)  # type: ignore # InlineKeyboardButton has no attribute same_line
        else:
            keyb.append([btn])
    return keyb



def revert_buttons(buttons: List[InlineKeyboardButton]) -> str:
    """
    Revert a list of InlineKeyboardButton to a string representation.

    This function assumes that the buttons have a `same_line` attribute and a `url`

    Args:
        buttons: A list of InlineKeyboardButton

    Returns:
        A string representation of the buttons.
    """
    res = ""
    for btn in buttons:
        if hasattr(btn, "same_line") and btn.same_line:
            res += "\n[{}](buttonurl://{}:same)".format(btn.text, btn.url) # type: ignore # InlineKeyboardButton has no attribute same_line
        else:
            res += "\n[{}](buttonurl://{})".format(btn.text, btn.url)
    return res



def is_module_loaded(name: str) -> bool:
    """
    Check if a module is loaded.

    Args:
        name: The name of the module.

    Returns:
        True if the module is loaded, False otherwise.
    """
    return (not LOAD or name in LOAD) and name not in NO_LOAD
