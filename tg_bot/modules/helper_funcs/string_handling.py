import logging
from typing import List, Optional, Tuple, Union

from telegram import Message, MessageEntity, User
from telegram.error import BadRequest
from telegram.ext import CallbackContext

from tg_bot import LOGGER  # Assuming this is your logger
from tg_bot.modules.users import get_user_id # Assuming this is your user id getter



def id_from_reply(message: Message) -> Tuple[Optional[int], Optional[str]]:
    """
    Extracts the user ID and any accompanying text from a message that is a reply
    to another message.

    Args:
        message: The Telegram message object.

    Returns:
        A tuple containing the user ID of the user who sent the original message
        (or None if the message is not a reply) and any text that follows the
        command in the current message.
    """
    prev_message = message.reply_to_message
    if not prev_message:
        return None, None
    user_id = prev_message.from_user.id
    text = message.text.split(None, 1)
    if len(text) < 2:
        return user_id, ""
    return user_id, text[1]


def extract_user(message: Message, args: List[str]) -> Optional[int]:
    """
    Extracts the user ID from a message and a list of arguments.  This function
    is a wrapper around extract_user_and_text that only returns the user ID.

    Args:
        message: The Telegram message object.
        args: A list of arguments extracted from the message text.

    Returns:
        The user ID of the target user, or None if no user could be extracted.
    """
    user_id, _ = extract_user_and_text(message, args)
    return user_id



def extract_user_and_text(
    message: Message, args: List[str]
) -> Tuple[Optional[int], Optional[str]]:
    """
    Extracts the user ID and any accompanying text from a message.  This function
    handles several cases:
    - Reply to a message
    - Text mention entity
    - Username mention (@username)
    - User ID (numeric)

    Args:
        message: The Telegram message object.
        args: A list of arguments extracted from the message text.

    Returns:
        A tuple containing the user ID and any text that follows the user
        identifier in the message.  Returns (None, None) if no user ID
        could be extracted.
    """
    prev_message = message.reply_to_message
    if message.text:
        split_text = message.text.split(None, 1)
    else:
        split_text = []

    if len(split_text) < 2 and not prev_message:
        return None, None  # No user ID found

    text = ""
    user_id = None

    if len(split_text) >= 2:
        text_to_parse = split_text[1]
    else:
        text_to_parse = ""
    
    entities = message.entities or [] # Handle None case
    
    for ent in entities:
        if ent.type == MessageEntity.TEXT_MENTION:
            if ent.offset == message.text.find(text_to_parse): # Check if the entity is the first argument
                user_id = ent.user.id
                text = message.text[ent.offset + ent.length :].strip()
                break # Important: Exit the loop after finding the relevant entity
    
    if user_id is None: # If user_id was not found in entities
        if len(args) >= 1:
            if args[0].startswith("@"):
                user = args[0]
                user_id = get_user_id(user)
                if not user_id:
                    message.reply_text(
                        "I don't have that user in my db. You'll be able to interact with them if "
                        "you reply to that person's message instead, or forward one of that user's messages."
                    )
                    return None, None
                if len(args) > 1:
                    text = message.text.split(None, 2)[2].strip()
            elif args[0].isdigit():
                user_id = int(args[0])
                if len(args) > 1:
                    text = message.text.split(None, 2)[2].strip()

    if user_id is None and prev_message:
        user_id, text = id_from_reply(message)

    if user_id:
        try:
            message.bot.get_chat(user_id)
        except BadRequest as excp:
            if excp.message in ("User_id_invalid", "Chat not found"):
                message.reply_text(
                    "I don't seem to have interacted with this user before - please forward a message from "
                    "them to give me control! (like a voodoo doll, I need a piece of them to be able "
                    "to execute certain commands...)"
                )
            else:
                LOGGER.exception("Exception %s on user %s", excp.message, user_id)
            return None, None

    return user_id, text



def extract_text(message: Message) -> str:
    """
    Extracts the text from a message, handling different message types.

    Args:
        message: The Telegram message object.

    Returns:
        The extracted text, or an empty string if no text is found.
    """
    if message.text:
        return message.text
    elif message.caption:
        return message.caption
    elif message.sticker:
        return message.sticker.emoji or ""  # Return empty string if no emoji
    else:
        return ""
