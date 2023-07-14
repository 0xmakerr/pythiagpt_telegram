import logging
import asyncio
import os
import re
from time import time
from dotenv import load_dotenv
from base_prompt import TIMEOUT_MSG
from pythgpt import pyth_gpt
from telegrambot import send_action
from telegram import Update
from telegram.ext import ContextTypes, ApplicationHandlerStop, Application, MessageHandler, filters
from telegram.constants import ChatAction

load_dotenv()
TELEGRAM_API_KEY = os.getenv('TELEGRAM_API_KEY')
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
MAX_USAGE = 1


@send_action(ChatAction.TYPING)
async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["restrictSince"] = time()

    placeholder_message = await context.bot.send_message(chat_id=update.effective_chat.id, text="...")
    user_message = update.message.text
    clean_user_message = re.sub(r"(^/chat|^@pythiatest_bot)", "", user_message).strip()
    answer = await asyncio.to_thread(pyth_gpt, message=clean_user_message)
    await context.bot.edit_message_text(chat_id=placeholder_message.chat_id, message_id=placeholder_message.message_id, parse_mode="Markdown", text=answer)


async def timeout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    count = context.user_data.get("usageCount", 0)
    restrict_since = context.user_data.get("restrictSince", 0)

    if restrict_since:
        if (time() - restrict_since) >= 30 * 60:  # 30 minutes
            del context.user_data["restrictSince"]
            del context.user_data["usageCount"]
        else:
            await update.effective_message.reply_text(parse_mode="Markdown", text=TIMEOUT_MSG)
            raise ApplicationHandlerStop
    context.user_data["usageCount"] = count + 1


if __name__ == '__main__':
    app = Application.builder().token(TELEGRAM_API_KEY).build()

    timeout_handler = MessageHandler(filters.Entity(entity_type="mention") | filters.Regex(re.compile('^/chat', re.IGNORECASE)), timeout)
    app.add_handler(timeout_handler, -1)

    chat_handler = MessageHandler(filters.Entity(entity_type="mention") | filters.Regex(re.compile('^/chat', re.IGNORECASE)), chat)
    app.add_handler(chat_handler, 0)

    app.run_polling()
