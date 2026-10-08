from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "AI Interview Service"
    app_version: str = "1.0.0"
    app_description: str = "This is a FastAPI application that provides an AI-powered interview service. It allows users to conduct mock interviews, receive feedback, and improve their interview skills using advanced AI algorithms."
    debug: bool = True

    openrouter_api_key: str


    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )

settings = Settings()