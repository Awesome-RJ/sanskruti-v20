from functools import wraps
from typing import Optional, Callable, Coroutine, Any

from telegram import User, Chat, ChatMember, Update, Bot
from telegram.error import BadRequest

from tg_bot import DEL_CMDS, SUDO_USERS, WHITELIST_USERS


# In PTB 20, the Bot class is passed directly, and Application instance is not used in these functions.
# The need to get bot instance using get_bot() is removed.

async def can_delete(chat: Chat, bot_id: int) -> bool:
    """Check if the bot can delete messages in the given chat.

    Args:
        chat: The Telegram chat.
        bot_id: The ID of the bot.

    Returns:
        True if the bot can delete messages, False otherwise.
    """
    try:
        member = await chat.get_member(bot_id)  # Await the coroutine
        return member.can_delete_messages
    except BadRequest:
        # Handle the specific exception if the bot isn't in the chat or other issues.
        return False  # Or raise, depending on desired behavior
    except Exception as e:
        # Log other errors
        print(f"Error in can_delete: {e}")
        return False



async def is_user_ban_protected(chat: Chat, user_id: int, member: ChatMember = None) -> bool:
    """Check if a user is protected from being banned.

    Args:
        chat: The Telegram chat.
        user_id: The ID of the user.
        member: Optional ChatMember object.  If provided, avoids an API call.

    Returns:
        True if the user is protected, False otherwise.
    """
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
        except Exception as e:
            print(f"Error in is_user_ban_protected: {e}")
            return False
    return member.status in ("administrator", "creator")



async def is_user_admin(chat: Chat, user_id: int, member: ChatMember = None) -> bool:
    """Check if a user is an admin in the given chat.

    Args:
        chat: The Telegram chat.
        user_id: The ID of the user.
        member: Optional ChatMember object. If provided, avoids an API call.

    Returns:
        True if the user is an admin, False otherwise.
    """
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
        except Exception as e:
            print(f"Error in is_user_admin: {e}")
            return False
    return member.status in ("administrator", "creator")



async def is_bot_admin(chat: Chat, bot_id: int, bot_member: ChatMember = None) -> bool:
    """Check if the bot is an admin in the given chat.

    Args:
        chat: The Telegram chat.
        bot_id: The ID of the bot.
        bot_member: Optional ChatMember object. If provided, avoids an API call.

    Returns:
        True if the bot is an admin, False otherwise.
    """
    if chat.type == "private" or chat.all_members_are_administrators:
        return True

    if not bot_member:
        try:
            bot_member = await chat.get_member(bot_id) # Await
        except BadRequest:
            return False
        except Exception as e:
            print(f"Error in is_bot_admin: {e}")
            return False
    return bot_member.status in ("administrator", "creator")



async def is_user_in_chat(chat: Chat, user_id: int) -> bool:
    """Check if a user is in the given chat.

    Args:
        chat: The Telegram chat.
        user_id: The ID of the user.

    Returns:
        True if the user is in the chat, False otherwise.
    """
    try:
        member = await chat.get_member(user_id) # Await
        return member.status not in ("left", "kicked")
    except BadRequest:
        return False  # Or raise
    except Exception as e:
        print(f"Error in is_user_in_chat: {e}")
        return False



def bot_can_delete(func: Callable[..., Coroutine[Any, Any, Any]]) -> Callable[..., Coroutine[Any, Any, Any]]:
    """Decorator to check if the bot can delete messages.

    Args:
        func: The function to decorate.

    Returns:
        The decorated function.
    """
    @wraps(func)
    async def delete_rights(bot: Bot, update: Update, *args, **kwargs) -> Any:
        if await can_delete(update.effective_chat, bot.id): # Await
            return await func(bot, update, *args, **kwargs) # Await
        else:
            try:
                await update.effective_message.reply_text( # Await
                    "I can't delete messages here! "
                    "Make sure I'm admin and can delete other user's messages."
                )
            except Exception as e:
                print(f"Error in bot_can_delete: {e}")

    return delete_rights



def can_pin(func: Callable[..., Coroutine[Any, Any, Any]]) -> Callable[..., Coroutine[Any, Any, Any]]:
    """Decorator to check if the bot can pin messages.

    Args:
        func: The function to decorate.

    Returns:
        The decorated function.
    """
    @wraps(func)
    async def pin_rights(bot: Bot, update: Update, *args, **kwargs) -> Any:
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
        except Exception as e:
            print(f"Error in can_pin: {e}")

    return pin_rights



def can_promote(func: Callable[..., Coroutine[Any, Any, Any]]) -> Callable[..., Coroutine[Any, Any, Any]]:
    """Decorator to check if the bot can promote members.

    Args:
        func: The function to decorate.

    Returns:
        The decorated function.
    """
    @wraps(func)
    async def promote_rights(bot: Bot, update: Update, *args, **kwargs) -> Any:
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
        except Exception as e:
            print(f"Error in can_promote: {e}")

    return promote_rights



def can_restrict(func: Callable[..., Coroutine[Any, Any, Any]]) -> Callable[..., Coroutine[Any, Any, Any]]:
    """Decorator to check if the bot can restrict members.

    Args:
        func: The function to decorate.

    Returns:
        The decorated function.
    """
    @wraps(func)
    async def restrict_rights(bot: Bot, update: Update, *args, **kwargs) -> Any:
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
        except Exception as e:
            print(f"Error in can_restrict: {e}")
    return restrict_rights



def bot_admin(func: Callable[..., Coroutine[Any, Any, Any]]) -> Callable[..., Coroutine[Any, Any, Any]]:
    """Decorator to check if the bot is an admin.

    Args:
        func: The function to decorate.

    Returns:
        The decorated function.
    """
    @wraps(func)
    async def is_admin(bot: Bot, update: Update, *args, **kwargs) -> Any:
        if await is_bot_admin(update.effective_chat, bot.id): #Await
            return await func(bot, update, *args, **kwargs) #Await
        else:
            await update.effective_message.reply_text("I'm not admin!") #Await

    return is_admin



def user_admin(func: Callable[..., Coroutine[Any, Any, Any]]) -> Callable[..., Coroutine[Any, Any, Any]]:
    """Decorator to check if the user is an admin.

    Args:
        func: The function to decorate.

    Returns:
        The decorated function.
    """
    @wraps(func)
    async def is_admin(bot: Bot, update: Update, *args, **kwargs) -> Any:
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
            except Exception as e:
                print(f"Error in user_admin (delete): {e}")

        else:
            try:
                await update.effective_message.reply_text("Who dis non-admin telling me what to do?") #Await
            except Exception as e:
                print(f"Error in user_admin (reply): {e}")

    return is_admin



def user_admin_no_reply(func: Callable[..., Coroutine[Any, Any, Any]]) -> Callable[..., Coroutine[Any, Any, Any]]:
    """Decorator to check if the user is an admin, without replying.

    Args:
        func: The function to decorate.

    Returns:
        The decorated function.
    """
    @wraps(func)
    async def is_admin(bot: Bot, update: Update, *args, **kwargs) -> Any:
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
            except Exception as e:
                print(f"Error in user_admin_no_reply: {e}")
    return is_admin



def user_not_admin(func: Callable[..., Coroutine[Any, Any, Any]]) -> Callable[..., Coroutine[Any, Any, Any]]:
    """Decorator to check if the user is not an admin.

    Args:
        func: The function to decorate.

    Returns:
        The decorated function.
    """
    @wraps(func)
    async def is_not_admin(bot: Bot, update: Update, *args, **kwargs) -> Any:
        user = update.effective_user  # type: Optional[User]
        if user and not await is_user_admin(update.effective_chat, user.id): #Await
            return await func(bot, update, *args, **kwargs) #Await

    return is_not_admin
