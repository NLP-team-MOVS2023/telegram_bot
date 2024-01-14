import asyncio
import json
import logging
import time
import os
import pandas as pd

from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiohttp import web
from magic_filter import F
from typing import Optional
from aiogram.filters.callback_data import CallbackData
from aiogram.enums import ParseMode
from aiogram import html
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

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


class NumbersCallbackFactory(CallbackData, prefix="fabnum"):
    action: str
    value: Optional[int] = None


json_file = 'feedback_ratings.json'

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
        types.KeyboardButton(text="Как пользоваться этим сервисом"),
    )
    builder.row(
        types.KeyboardButton(text="Сделать предсказание"),
    )
    builder.row(types.KeyboardButton(
        text="Оценить работу сервиса")
    )
    builder.row(types.KeyboardButton(
        text="Вывести статистику по сервису")
    )
    await message.answer(
        "Этот бот создан в рамках годового проекта по извлечению деталей из текста в магистратуре МОВС.\n" \
        'чтобы узнать, какие функции имеет бот, напишите /help\n' \
        'если хотите снова увидеть стартовое меню кнопок, напишите /start\n',
        'чтобы оценить работу бота, напишите /feedback\n',
        'чтобы вывести статистику оценок, напишите /rating\n',
        reply_markup=builder.as_markup(resize_keyboard=True))



@dp.message(Command("help"))
@dp.message(F.text.lower() == "как пользоваться этим сервисом")
async def cmd_special_buttons(message: types.Message):
    text = 'Данный бот умеет делать предсказания о предикатном отношении между двумя сущностями (например, предикатом будет __on__ для сущностей ___book___ и ___table___).\n' \
    'Чтобы сделать предсказания, необходимо загрузить файл формата .csv с колонками __objects__ и __subjects__.',
    await message.answer(text, parse_mode=ParseMode.MARKDOWN)


@dp.message(F.text.lower() == "сделать предсказание")
async def user_experiense(message: types.Message):
    await message.answer(
        "Пожалуйста, загрузите файл формата .csv с колонками __objects__ и __subjects__.",
    )


@dp.message(F.document)
async def handle_file(message: types.Message):
    if message.document.mime_type == 'text/csv':
        file_bytes = await bot.download(message.document)

        # Read CSV file using pandas
        df = pd.read_csv(file_bytes)
        try:
            pass
            # item = prepare_data(df)
            # pred = predict(item)
        except:
            await message.answer("Пожалуйста, приложите файл необходимого формата")

        # if len(df) == 1:
        #     result_message = f"Предсказанная стоимость автомобиля {df['name'].values[0]}: {pred[0]:0.0f} руб."
        # elif len(df) > 1:
        #     result_message = 'Предсказанные стоимости автомобилей:\n'
        #     for i in range(len(df)):
        #         result_message += f"{df['name'].values[i]}: {pred[i]:0.0f} руб.\n"
        await message.answer('TBA', parse_mode=ParseMode.MARKDOWN)
    else:
        await message.answer("Пожалуйста, приложите файл необходимого формата")


@dp.message(Command("feedback"))
@dp.message(F.text.lower() == "оценить работу сервиса")
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
@dp.message(F.text.lower() == "вывести статистику по сервису")
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