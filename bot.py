import asyncio
import json
import logging
import time

import pandas as pd

from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from magic_filter import F
from typing import Optional
from aiogram.filters.callback_data import CallbackData
from aiogram.enums import ParseMode
from aiogram import html

from config_reader import config

logging.basicConfig(level=logging.INFO)

bot = Bot(token=config.bot_token.get_secret_value())

dp = Dispatcher()


class NumbersCallbackFactory(CallbackData, prefix="fabnum"):
    action: str
    value: Optional[int] = None


json_file = 'feedback_ratings.json'

try:
    with open(json_file, 'r') as file:
        feedback_ratings = json.load(file)
except FileNotFoundError:
    feedback_ratings = {}


# ПОЛИНА: тут менять
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    print(feedback_ratings)
    if user_id not in feedback_ratings:
        feedback_ratings[user_id] = {}
    await message.answer(
        "Приветствую! Тут вы можете подать на вход несколько данных о пользователе и получить предсказание")


# ПОЛИНА: тут менять
@dp.message(Command("help"))
async def cmd_special_buttons(message: types.Message):
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
        "Выберите действие:",
        reply_markup=builder.as_markup(resize_keyboard=True),
    )


# ПОЛИНА: тут менять
@dp.message(F.text.lower() == "как пользоваться этим сервисом")
async def user_experiense(message: types.Message):
    text = 'Данный бот умеет:\n' \
           '• делать предсказания по одному экземпляру-автомобилю, шаблон высылается\n' \
           '• делать предсказания по батчу автомобилей'

    await message.answer(text, parse_mode=ParseMode.MARKDOWN)


# ПОЛИНА: тут менять (пока написать заглушкитипа coming soon)
@dp.message(F.text.lower() == "сделать предсказание")
async def user_experiense(message: types.Message):
    await message.answer(
        "Предсказания для скольки автомобилей вы хотите сделать?",
    )


# ПОЛИНА: тут менять
@dp.message(F.document)
async def handle_file(message: types.Message):
    print(message.document)
    if message.document.mime_type == 'text/csv':
        # file_id = message.document.file_id
        # file_info = await bot.get_file(file_id)
        file_bytes = await bot.download(message.document)

        # Read CSV file using pandas
        df = pd.read_csv(file_bytes)
        print(df)

        # Make predictions using the ML model
        # predictions = model.predict(df)

        # Send the predictions back to the user
        if len(df) == 1:
            result_message = "Предсказанная стоимость автомобиля: 120 000 руб."# + str(predictions)
            # await message.answer(result_message, parse_mode=ParseMode.MARKDOWN)
        elif len(df) > 1:
            result_message = 'Предсказанные стоимости автомобилей:'
            for i in range(len(df)):
                result_message += f"{i+1}: 120 000 руб.\n"
        await message.answer(result_message, parse_mode=ParseMode.MARKDOWN)
    else:
        await message.answer("Пожалуйста, приложите файл необходимого формата")




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

    feedback_ratings[user_id][timestamp] = rating

    # Save the feedback dictionary to the JSON file
    with open(json_file, 'w') as file:
        json.dump(feedback_ratings, file)
    await callback.message.answer("Благодарю за отзыв!")


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
    # val_rating = list(feedback_ratings.values())
    # print(val_rating)
    await message.answer(
        f"Всего уникальных пользователей: {len(feedback_ratings.keys())}\nОценили сервис: {len(users)} юзеров\nСредняя оценка сервиса: {summ / n if n > 0 else 0:0.2f}",
    )


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
