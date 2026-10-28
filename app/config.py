from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "AI Interview Service"
    app_version: str = "1.0.0"
    app_description: str = "This is a FastAPI application that provides an AI-powered interview service. It allows users to conduct mock interviews, receive feedback, and improve their interview skills using advanced AI algorithms."
    debug: bool = True

    openrouter_api_key: str
    openrouter_base_url: str
    ai_model: str

    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    database_url: str

    # Comma-separated list of origins allowed to call the API from a browser
    cors_origins: str

    google_client_id: str
    google_client_secret: str
    google_redirect_uri: str = "http://localhost:8000/auth/google/callback"
    session_secret_key: str
    frontend_url: str = "http://localhost:3000"

    redis_url: str

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

settings = Settings()