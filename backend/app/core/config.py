from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "SoranoGear Commerce & Support"
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60
    DATABASE_URL: str = "sqlite:///./commerce.db"
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    OLLAMA_BASE_URL: str = "http://127.0.0.1:11434"
    OLLAMA_MODEL: str = "llama3.2:1b"

    AI_FALLBACK_BASE_URL: str = ""
    AI_FALLBACK_API_KEY: str = ""
    AI_FALLBACK_MODEL: str = ""

    UPLOAD_DIR: str = "./uploads"

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()
