# -*- coding: utf-8 -*-
"""
Telegram-агентство «Спроси Хелен» — режим штаба.
Ты пишешь задачу в Telegram, бот отвечает в голосе Хелен через Claude.
Запуск: python main.py  (нужны переменные окружения, см. .env.example и README)
"""

import os
import logging
from collections import defaultdict, deque

import anthropic
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

from prompts import SYSTEM, QUICK_TASKS, WELCOME

# --- Настройки из окружения ---
BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")
# Кто может пользоваться ботом. Пусто = все. Иначе список Telegram user id через запятую.
ALLOWED = {x.strip() for x in os.environ.get("ALLOWED_USER_IDS", "").split(",") if x.strip()}

MAX_TOKENS = 2000
HISTORY_TURNS = 6  # сколько последних реплик помнит бот (контекст диалога)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("helen-agency")

client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

# Память диалога на пользователя: deque из {"role","content"}
history = defaultdict(lambda: deque(maxlen=HISTORY_TURNS * 2))


def allowed(update: Update) -> bool:
    if not ALLOWED:
        return True
    user = update.effective_user
    return user is not None and str(user.id) in ALLOWED


def menu_keyboard() -> InlineKeyboardMarkup:
    buttons, row = [], []
    for key, (label, _) in QUICK_TASKS.items():
        row.append(InlineKeyboardButton(label, callback_data=key))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(buttons)


async def ask_claude(user_id: int, user_text: str) -> str:
    """Отправляет задачу в Claude с памятью диалога и возвращает ответ."""
    h = history[user_id]
    h.append({"role": "user", "content": user_text})
    try:
        resp = await client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=SYSTEM,
            messages=list(h),
        )
        answer = "".join(block.text for block in resp.content if block.type == "text").strip()
    except Exception as e:  # noqa: BLE001
        log.exception("Claude error")
        h.pop()  # не сохраняем неудачную реплику
        return f"Не получилось ответить. Техническая ошибка: {e}"
    h.append({"role": "assistant", "content": answer})
    return answer


async def send_long(update: Update, text: str) -> None:
    """Telegram режет сообщения длиннее ~4096 символов. Шлём частями."""
    limit = 4000
    chunks = [text[i : i + limit] for i in range(0, len(text), limit)] or ["(пусто)"]
    for chunk in chunks:
        await update.effective_message.reply_text(chunk)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not allowed(update):
        await update.message.reply_text("Этот штаб приватный.")
        return
    await update.message.reply_text(WELCOME, reply_markup=menu_keyboard())


async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    history[update.effective_user.id].clear()
    await update.message.reply_text("Контекст очищен. Начинаем с чистого листа.")


async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not allowed(update):
        return
    label, task = QUICK_TASKS[query.data]
    await query.message.reply_text(f"{label}\nГотовлю...")
    answer = await ask_claude(update.effective_user.id, task)
    await send_long(update, answer)


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not allowed(update):
        await update.message.reply_text("Этот штаб приватный.")
        return
    await update.effective_chat.send_action("typing")
    answer = await ask_claude(update.effective_user.id, update.message.text)
    await send_long(update, answer)


def main() -> None:
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("menu", cmd_start))
    app.add_handler(CommandHandler("reset", cmd_reset))
    app.add_handler(CallbackQueryHandler(on_button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    log.info("Агентство Хелен запущено. Модель: %s", MODEL)
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
