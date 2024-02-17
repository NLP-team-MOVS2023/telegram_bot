import sys
import json
from typing import Optional

import pytest
from unittest.mock import patch, ANY, AsyncMock, call

import requests
from requests.exceptions import HTTPError

from aiogram import types
from aiogram.enums import ParseMode
from aiogram.filters.callback_data import CallbackData
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

sys.path.append("./")
import bot
from bot import feedback_ratings
import message_texts
from config_reader import config

allowed_requests = [
    "Как пользоваться этим сервисом",
    "Сделать предсказание",
    "Оценить работу сервиса",
    "Вывести статистику по сервису",
]


@patch("builtins.open")
def test_load_feedback_ratings_nofile(open_mock):
    open_mock.return_value.__enter__.side_effect = FileNotFoundError
    assert bot.load_feedback_ratings() == {}
    open_mock.assert_called_once()


@patch.dict(feedback_ratings, {}, clear=True)
def test_load_feedback_ratings_file(full_json):
    assert bot.load_feedback_ratings() == {
        "1": {"123456": 5},
        "2": {"567890": 3},
        "3": {},
    }


@pytest.mark.asyncio
@patch.dict(feedback_ratings, {}, clear=True)
async def test_cmd_start(empty_json):
    message = AsyncMock()
    message.from_user.id = "1"

    builder = ReplyKeyboardBuilder()
    builder.row(
        types.KeyboardButton(text=allowed_requests[0]),
    )
    builder.row(
        types.KeyboardButton(text=allowed_requests[1]),
    )
    builder.row(types.KeyboardButton(text=allowed_requests[2]))
    builder.row(types.KeyboardButton(text=allowed_requests[3]))

    await bot.cmd_start(message)
    message.answer.assert_called_with(
        message_texts.start,
        reply_markup=builder.as_markup(resize_keyboard=True)
    )
    assert feedback_ratings["1"] == {}


@pytest.mark.asyncio
async def test_cmd_help():
    message = AsyncMock()

    await bot.cmd_help(message)
    message.answer.assert_called_with(
        message_texts.help,
        parse_mode=ParseMode.MARKDOWN
    )


@pytest.mark.asyncio
async def test_cmd_predict():
    message = AsyncMock()

    await bot.cmd_predict(message)
    message.answer.assert_called_with(
        message_texts.predict, parse_mode=ParseMode.MARKDOWN
    )


@pytest.mark.asyncio
@patch.object(bot.bot, "download", return_value=open(r"tests\data\data.csv"))
@patch.object(bot.bot, "send_document")
@patch.object(requests, "post")
async def test_make_predictions(post, send_document, download):
    # кейс с неверным расширением
    message = AsyncMock()
    message.document.mime_type = "not valid"

    await bot.make_predictions(message)
    message.answer.assert_called_with(message_texts.invalid_format)

    # кейс с верным расширением
    message = AsyncMock()
    message.document.mime_type = "text/csv"
    message.chat.id = "1"

    post.return_value.text = str({"1": "4"})
    post.return_value.status_code = 200
    post.return_value.raise_for_statue.side_effect = None

    await bot.make_predictions(message)

    message.answer.assert_called_with(message_texts.processing)
    download.assert_called_with(message.document)
    send_document.assert_called_with(
        "1",
        ANY,
        caption=message_texts.predictions
    )
    assert isinstance(
        send_document.call_args.args[1], types.input_file.BufferedInputFile
    )


@pytest.mark.asyncio
@patch.object(bot.bot, "download", return_value=open(r"tests\data\data.csv"))
@patch.object(requests, "post")
async def test_make_predictions_500(post, download):
    message = AsyncMock()
    message.document.mime_type = "text/csv"
    message.chat.id = "1"

    post.return_value.text = None
    post.return_value.status_code = 500
    post.return_value.raise_for_status.side_effect = HTTPError()

    await bot.make_predictions(message)

    download.assert_called_with(message.document)
    message.answer.has_calls(
        [call(message_texts.processing), call(message_texts.connection_error)],
        any_order=False,
    )


class NumbersCallbackFactory(CallbackData, prefix="fabnum"):
    action: str
    value: Optional[int] = None


@pytest.mark.asyncio
async def test_feedback():
    message = AsyncMock()
    message.from_user.id = "1"

    builder = InlineKeyboardBuilder()
    for i in range(1, 6):
        builder.button(
            text=str(i),
            callback_data=NumbersCallbackFactory(action="feedback", value=i),
        )
    builder.adjust(5)

    await bot.feedback(message)
    message.answer.assert_called_with(
        message_texts.feedback,
        reply_markup=builder.as_markup(resize_keyboard=True)
    )


@pytest.mark.asyncio
@patch("time.time", return_value=123456)
@patch.dict(feedback_ratings, {}, clear=True)
async def test_callbacks_num_change_fab(time):
    callback = AsyncMock()
    callback.from_user.id = "1"
    callback_data = AsyncMock()
    callback_data = NumbersCallbackFactory(action="feedback", value=5)

    await bot.callbacks_num_change_fab(callback, callback_data)

    assert feedback_ratings["1"]["123456"] == 5
    with open(config.json_file, "rb") as f:
        res_json = json.load(f)

    assert res_json["1"]["123456"] == 5
    callback.message.answer.assert_called_with(message_texts.thanks)


@pytest.mark.asyncio
async def test_feedback_stats_existent(full_json):
    message = AsyncMock()

    await bot.feedback_stats(message)

    message.answer.assert_called_with(
        message_texts.feedback_report.format(3, 2, 4.00)
    )


@pytest.mark.asyncio
async def test_feedback_stats_nonexistent(empty_json):
    message = AsyncMock()

    await bot.feedback_stats(message)

    message.answer.assert_called_with(message_texts.no_feedback)


@pytest.mark.asyncio
@patch("builtins.open")
async def test_feedback_stats_nofile(open, empty_json):
    message = AsyncMock()
    open.side_effect = FileNotFoundError()

    await bot.feedback_stats(message)

    message.answer.assert_called_with(message_texts.no_feedback)


@pytest.mark.asyncio
async def test_not_allowed():
    message = AsyncMock()

    await bot.not_allowed(message)

    message.answer.assert_called_with(message_texts.invalid_cmd)
