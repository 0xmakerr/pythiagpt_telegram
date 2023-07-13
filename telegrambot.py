from telegram.ext.filters import MessageFilter
from functools import wraps


class FilterChat(MessageFilter):
    def filter(self, message):
        return '/chat' in message.text


def send_action(action):
    """Sends `action` while processing func command."""
    def decorator(func):
        @wraps(func)
        async def command_func(update, context, *args, **kwargs):
            await context.bot.send_chat_action(chat_id=update.effective_message.chat_id, action=action)
            return await func(update, context, *args, **kwargs)
        return command_func
    return decorator
