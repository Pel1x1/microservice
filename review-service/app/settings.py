from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    postgres_url: str = 'postgresql://postgres:password@localhost:5432/postgres'
    order_url: str = 'http://localhost:8002'

    model_config = SettingsConfigDict(env_file='.env', extra='ignore')


settings = Settings()
