from functools import wraps
from typing import Optional

from telegram import User, Chat, ChatMember, Update, Bot
from telegram.error import BadRequest

from tg_bot import DEL_CMDS, SUDO_USERS, WHITELIST_USERS

# In PTB 20, the Bot class is passed directly, and Application instance is not used in these functions.
#  The need to get bot instance using get_bot() is removed.

async def can_delete(chat: Chat, bot_id: int) -> bool:
    """Check if the bot can delete messages in the given chat."""
    try:
        member = await chat.get_member(bot_id)  # Await the coroutine
        return member.can_delete_messages
    except BadRequest:
        # Handle the specific exception if the bot isn't in the chat or other issues.
        return False  # Or raise, depending on desired behavior


async def is_user_ban_protected(chat: Chat, user_id: int, member: ChatMember = None) -> bool:
    """Check if a user is protected from being banned."""
    if (
        chat.type == "private"
        or user_id in SUDO_USERS
        or user_id in WHITELIST_USERS
        or chat.all_members_are_administrators
    ):
        return True

    if not member:
        try:
            member = await chat.get_member(user_id)  # Await
        except BadRequest:
            return False  # Or raise
    return member.status in ("administrator", "creator")



async def is_user_admin(chat: Chat, user_id: int, member: ChatMember = None) -> bool:
    """Check if a user is an admin in the given chat."""
    if (
        chat.type == "private"
        or user_id in SUDO_USERS
        or chat.all_members_are_administrators
    ):
        return True

    if not member:
        try:
            member = await chat.get_member(user_id) # Await
        except BadRequest:
            return False # Or raise
    return member.status in ("administrator", "creator")



async def is_bot_admin(chat: Chat, bot_id: int, bot_member: ChatMember = None) -> bool:
    """Check if the bot is an admin in the given chat."""
    if chat.type == "private" or chat.all_members_are_administrators:
        return True

    if not bot_member:
        try:
            bot_member = await chat.get_member(bot_id) # Await
        except BadRequest:
            return False
    return bot_member.status in ("administrator", "creator")



async def is_user_in_chat(chat: Chat, user_id: int) -> bool:
    """Check if a user is in the given chat."""
    try:
        member = await chat.get_member(user_id) # Await
        return member.status not in ("left", "kicked")
    except BadRequest:
        return False  # Or raise



def bot_can_delete(func):
    """Decorator to check if the bot can delete messages."""

    @wraps(func)
    async def delete_rights(bot: Bot, update: Update, *args, **kwargs):
        if await can_delete(update.effective_chat, bot.id): # Await
            return await func(bot, update, *args, **kwargs) # Await
        else:
            await update.effective_message.reply_text( # Await
                "I can't delete messages here! "
                "Make sure I'm admin and can delete other user's messages."
            )

    return delete_rights


def can_pin(func):
    """Decorator to check if the bot can pin messages."""

    @wraps(func)
    async def pin_rights(bot: Bot, update: Update, *args, **kwargs):
        try:
            member = await update.effective_chat.get_member(bot.id) # Await
            if member.can_pin_messages:
                return await func(bot, update, *args, **kwargs) # Await
            else:
                await update.effective_message.reply_text(  # Await
                    "I can't pin messages here! "
                    "Make sure I'm admin and can pin messages."
                )
        except BadRequest:
             await update.effective_message.reply_text(  # Await
                    "I can't pin messages here! "
                    "Make sure I'm admin and can pin messages."
                )

    return pin_rights



def can_promote(func):
    """Decorator to check if the bot can promote members."""

    @wraps(func)
    async def promote_rights(bot: Bot, update: Update, *args, **kwargs):
        try:
            member = await update.effective_chat.get_member(bot.id) # Await
            if member.can_promote_members:
                return await func(bot, update, *args, **kwargs) #Await
            else:
                await update.effective_message.reply_text( #Await
                    "I can't promote/demote people here! "
                    "Make sure I'm admin and can appoint new admins."
                )
        except BadRequest:
            await update.effective_message.reply_text( #Await
                    "I can't promote/demote people here! "
                    "Make sure I'm admin and can appoint new admins."
                )

    return promote_rights



def can_restrict(func):
    """Decorator to check if the bot can restrict members."""

    @wraps(func)
    async def restrict_rights(bot: Bot, update: Update, *args, **kwargs):
        try:
            member = await update.effective_chat.get_member(bot.id) #Await
            if member.can_restrict_members:
                return await func(bot, update, *args, **kwargs) #Await
            else:
                 await update.effective_message.reply_text( #Await
                    "I can't restrict people here! "
                    "Make sure I'm admin and can appoint new admins."
                )
        except BadRequest:
            await update.effective_message.reply_text( #Await
                    "I can't restrict people here! "
                    "Make sure I'm admin and can appoint new admins."
                )
    return restrict_rights



def bot_admin(func):
    """Decorator to check if the bot is an admin."""

    @wraps(func)
    async def is_admin(bot: Bot, update: Update, *args, **kwargs):
        if await is_bot_admin(update.effective_chat, bot.id): #Await
            return await func(bot, update, *args, **kwargs) #Await
        else:
            await update.effective_message.reply_text("I'm not admin!") #Await

    return is_admin



def user_admin(func):
    """Decorator to check if the user is an admin."""

    @wraps(func)
    async def is_admin(bot: Bot, update: Update, *args, **kwargs):
        user = update.effective_user  # type: Optional[User]
        if user and await is_user_admin(update.effective_chat, user.id): #Await
            return await func(bot, update, *args, **kwargs) #Await

        elif not user:
            pass

        elif DEL_CMDS and " " not in update.effective_message.text:
            try:
                await update.effective_message.delete() #Await
            except BadRequest:
                pass #Do nothing if you don't have permissions

        else:
            await update.effective_message.reply_text("Who dis non-admin telling me what to do?") #Await

    return is_admin



def user_admin_no_reply(func):
    """Decorator to check if the user is an admin, without replying."""

    @wraps(func)
    async def is_admin(bot: Bot, update: Update, *args, **kwargs):
        user = update.effective_user  # type: Optional[User]
        if user and await is_user_admin(update.effective_chat, user.id): #Await
            return await func(bot, update, *args, **kwargs) #Await

        elif not user:
            pass

        elif DEL_CMDS and " " not in update.effective_message.text:
            try:
                await update.effective_message.delete() #Await
            except BadRequest:
                pass #Do nothing if you don't have permissions
    return is_admin


def user_not_admin(func):
    """Decorator to check if the user is not an admin."""

    @wraps(func)
    async def is_not_admin(bot: Bot, update: Update, *args, **kwargs):
        user = update.effective_user  # type: Optional[User]
        if user and not await is_user_admin(update.effective_chat, user.id): #Await
            return await func(bot, update, *args, **kwargs) #Await

    return is_not_admin
