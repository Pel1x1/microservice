from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    postgres_url: str = 'postgresql://postgres:password@localhost:5432/postgres'
    amqp_url: str = 'amqp://guest:guest@localhost:5672/'
    exchange: str = 'automarket'
    queue_prefix: str = 'ikbo-65-23_automarket'

    model_config = SettingsConfigDict(env_file='.env', extra='ignore')


settings = Settings()
