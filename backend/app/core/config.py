from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    postgres_user: str
    postgres_password: str
    postgres_db: str
    database_url: str

    secret_key: str
    access_token_expire_minutes: int = 60

    pydantic_ai_gateway_api_key: str = ""

    class Config:
        env_file = "../.env"  # backend/ -> project root .env
        extra = "ignore"


settings = Settings()