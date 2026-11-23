from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "AI Commerce Support"
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60
    DATABASE_URL: str = "sqlite:///./commerce.db"
    CORS_ORIGINS: str = "http://localhost:5173"
    class Config:
        env_file = ".env"

settings = Settings()