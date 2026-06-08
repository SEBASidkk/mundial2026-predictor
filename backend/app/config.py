from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite:///./mundial2026.db"
    football_data_api_key: str = ""
    openweather_api_key: str = ""
    cors_origins: str = "http://localhost:4200"

    class Config:
        env_file = ".env"


settings = Settings()
