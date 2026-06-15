from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str = "sqlite:///./mundial2026.db"
    football_data_api_key: str = ""
    openweather_api_key: str = ""
    odds_api_key: str = ""
    cors_origins: str = "http://localhost:4200"


settings = Settings()
