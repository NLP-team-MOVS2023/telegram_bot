import io
import json
import logging
import time
import os
from typing import Optional

import pandas as pd
import requests
import ast
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from aiogram.types import BufferedInputFile
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram import F
from aiogram.filters.callback_data import CallbackData
from aiogram.enums import ParseMode
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from config_reader import config

try:
    BOT_TOKEN = config.bot_token.get_secret_value()
except:
    BOT_TOKEN = os.getenv('BOT_TOKEN')

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot=bot)

WEBHOOK_HOST = 'https://nlp-team-ml-bot.onrender.com'
WEBHOOK_PATH = f'/webhook/{BOT_TOKEN}'
WEBHOOK_URL = f'{WEBHOOK_HOST}{WEBHOOK_PATH}'

allowed_requests = ["Как пользоваться этим сервисом", "Сделать предсказание", "Оценить работу сервиса",
                    "Вывести статистику по сервису"]


json_file = 'feedback_ratings.json'

class NumbersCallbackFactory(CallbackData, prefix="fabnum"):
    action: str
    value: Optional[int] = None


class PredictorsCallbackFactory(CallbackData, prefix="fabpred"):
    action: str
    value: Optional[int] = None

try:
    with open(json_file, 'r') as file:
        feedback_ratings = json.load(file)
except FileNotFoundError:
    feedback_ratings = {}


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    if user_id not in feedback_ratings:
        feedback_ratings[user_id] = {}
    builder = ReplyKeyboardBuilder()
    builder.row(
        types.KeyboardButton(text=allowed_requests[0]),
    )
    builder.row(
        types.KeyboardButton(text=allowed_requests[1]),
    )
    builder.row(types.KeyboardButton(
        text="Оценить работу сервиса")
    )
    builder.row(types.KeyboardButton(
        text="Вывести статистику по сервису")
    )
    await message.answer(
        "Этот бот создан в рамках годового проекта по извлечению деталей из текста в магистратуре МОВС.\n"
        'Чтобы узнать, какие функции имеет бот, напишите /help\n'
        'Чтобы сделать предсказание, напишите /predict\n'
        'Чтобы оценить работу бота, напишите /feedback\n'
        'Чтобы вывести статистику оценок, напишите /rating\n'
        'Также все действия выше могут быть вызваны соответствующими кнопками.\n'
        'Если хотите снова увидеть стартовое меню кнопок, напишите /start\n',
        reply_markup=builder.as_markup(resize_keyboard=True))


@dp.message(Command("help"))
@dp.message(F.text.lower() == allowed_requests[0].lower())
async def cmd_help(message: types.Message):
    text = 'Данный бот умеет делать предсказания о предикатном отношении между двумя сущностями (например, предикатом ' \
           'для сущностей _book_ и _table_ будет _on_).\n' \
           'Чтобы сделать предсказания, необходимо загрузить файл формата .csv с колонками _objects_ и _subjects_.'
    await message.answer(text, parse_mode=ParseMode.MARKDOWN)


@dp.message(Command("predict"))
@dp.message(F.text.lower() == allowed_requests[1].lower())
async def cmd_predict(message: types.Message):
    await message.answer(
        "Пожалуйста, загрузите файл формата .csv с колонками _objects_ и _subjects_.", parse_mode=ParseMode.MARKDOWN
    )


# @dp.message(F.text.lower() == 'a')
# async def not_allowed(message: types.Message):
#     await message.answer(
#         "Бот Вас не понял :) Пожалуйста, воспользуйтесь предложенными функциями бота."
#     )


@dp.message(F.document)
async def make_predictions(message: types.Message):
    response = None
    if message.document.mime_type == 'text/csv':
        file_bytes = await bot.download(message.document)
        df = pd.read_csv(file_bytes)
        try:
            response = requests.post('https://nlp-project-movs.onrender.com/predict', json=df.to_dict(orient='list'))
        except:
            await message.answer("Пожалуйста, приложите файл необходимого формата")
    if response:
        response_dict = ast.literal_eval(response.text)
        response_df = pd.DataFrame(response_dict.values())
        response_csv = response_df.to_csv(index=False)
        predictions = BufferedInputFile(io.BytesIO(response_csv.encode()).getvalue(), filename="predictions.csv")
        await bot.send_document(message.chat.id, predictions, caption="Полученные предсказания:")
    else:
        await message.answer("Пожалуйста, приложите файл необходимого формата")


@dp.message(Command("feedback"))
@dp.message(F.text.lower() == allowed_requests[2].lower())
async def feedback(message: types.Message):
    builder = InlineKeyboardBuilder()
    for i in range(1, 6):
        builder.button(text=str(i), callback_data=NumbersCallbackFactory(action="feedback", value=i))
    builder.adjust(5)
    await message.answer(
        "Насколько вам понравилась работа телеграм бота?",
        reply_markup=builder.as_markup(resize_keyboard=True),
    )


@dp.callback_query(NumbersCallbackFactory.filter())
async def callbacks_num_change_fab(callback: types.CallbackQuery, callback_data: NumbersCallbackFactory):
    user_id = callback.from_user.id
    timestamp = int(time.time())
    # print(callback.message)
    rating = callback_data.value

    if user_id not in feedback_ratings:
        feedback_ratings[user_id] = {}

    feedback_ratings[user_id][timestamp] = rating

    with open(json_file, 'w') as file:
        json.dump(feedback_ratings, file)
    await callback.message.answer("Благодарю за отзыв!")


@dp.message(Command("rating"))
@dp.message(F.text.lower() == allowed_requests[3].lower())
async def feedback_stats(message: types.Message):
    with open(json_file, 'r') as file:
        feedback_ratings = json.load(file)
    n = 0
    summ = 0
    users = []
    for i in feedback_ratings:
        for j in feedback_ratings[i].values():
            users.append(i)
            n += 1
            summ += int(j)

    users = set(users)
    await message.answer(
        f"Всего уникальных пользователей: {len(feedback_ratings.keys())}\nОценили сервис: {len(users)} юзеров\nСредняя оценка сервиса: {summ / n if n > 0 else 0:0.2f}",
    )


async def on_startup(bot: Bot) -> None:
    await bot.set_webhook(url=WEBHOOK_URL)


async def on_shutdown(dp):
    await bot.delete_webhook()


def main():
    dp.startup.register(on_startup)
    app = web.Application()
    webhook_requests_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
    )
    webhook_requests_handler.register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)
    web.run_app(app, host='0.0.0.0', port=10000)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
