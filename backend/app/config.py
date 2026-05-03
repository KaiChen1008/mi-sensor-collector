from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_host: str = "0.0.0.0"
    app_port: int = 8000
    database_url: str = "sqlite+aiosqlite:///./data/sensors.db"
    scan_interval_seconds: int = 60
    # Set to true to generate fake readings (useful when no BLE hardware available)
    simulate_sensors: bool = False

    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""

    telegram_bot_token: str = ""

    line_notify_token: str = ""


settings = Settings()
