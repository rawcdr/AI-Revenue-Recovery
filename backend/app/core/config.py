from pydantic_settings import BaseSettings, SettingsConfigDict

from typing import Literal

class Settings(BaseSettings):
    INTELLIGENCE_MAX_BATCH: int = 500
    RECOVERY_MAX_BATCH: int = 100
    PAYMENT_EXECUTION_MODE: Literal["SIMULATED"] = "SIMULATED"
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
