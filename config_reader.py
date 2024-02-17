import os

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr


class Settings(BaseSettings):
    bot_token: SecretStr
    json_file: str = "data/feedback_ratings.json"
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')


class TestSettings(Settings):
    json_file: str = "tests/data/test_feedback_ratings.json"


def get_config() -> Settings:
    env_type: str | None = os.environ.get("ENV_TYPE")
    match env_type:
        case None:
            return Settings()
        case "test":
            return TestSettings()
        case "docker":
            raise NotImplementedError
        case _:
            raise ValueError(f"{env_type} is not supported")


config = get_config()
