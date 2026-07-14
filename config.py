"""全局配置，从 .env 加载。"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    output_format: str = "txt"
    output_dir: str = "./books"
    concurrency: int = 3
    request_interval: float = 1.5
    request_timeout: int = 30
    retry_times: int = 3
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )


settings = Settings()