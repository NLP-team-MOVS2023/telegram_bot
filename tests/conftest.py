import sys
import json
import datetime
import aiogram
import pytest

sys.path.append("./")
from config_reader import config


def clean_up():
    with open(config.json_file, 'w', encoding="utf-8") as f:
        json.dump({}, f, indent=4, sort_keys=True, ensure_ascii=False)


def fill_json():
    with open(config.json_file, "w", encoding="utf-8") as f:
        json.dump({"1": {"123456": 5}, "2": {"567890": 3}, "3": {}}, f, indent=4, sort_keys=True, ensure_ascii=False)


@pytest.fixture()
def empty_json():
    clean_up()
    yield
    clean_up()


@pytest.fixture()
def full_json():
    clean_up()
    fill_json()
    yield
    clean_up()


def make_message(
        text: str,
        from_user: aiogram.types.user.User = None,
        chat: aiogram.types.chat.Chat = None,
) -> aiogram.types.message.Message:
    return aiogram.types.message.Message(
        message_id=1,
        date=datetime.datetime.now(),
        chat=chat,
        from_user=from_user,
        text=text,
    )


def make_callback(
        data: str,
        from_user: aiogram.types.user.User = None,
        message: aiogram.types.message.Message = None,
) -> aiogram.types.callback_query.CallbackQuery:
    return aiogram.types.callback_query.CallbackQuery(
        id="12",
        from_user=from_user,
        # chat_instance: str,
        message=message,
        data=data,
    )


def make_user(
        id: int,
) -> aiogram.types.user.User:
    return aiogram.types.user.User(
        id=id,
        is_bot=False,
        first_name="Test",
        username="test_username",
    )


def make_chat(
        id: int,
) -> aiogram.types.chat.Chat:
    return aiogram.types.chat.Chat(
        id=id,
        type="private",
    )
