import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.schemas.base_schema import Base
import app.schemas.delivery  # noqa: F401  регистрирует таблицы в Base.metadata

POSTGRES_URL = os.getenv('POSTGRES_URL', 'postgresql://postgres:password@localhost:5432/postgres')


@pytest.fixture(scope='session')
def engine():
    engine = create_engine(POSTGRES_URL)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture()
def db(engine) -> Session:
    """Отдельная сессия на тест; после теста таблицы очищаются."""
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    yield session
    session.rollback()
    for table in reversed(Base.metadata.sorted_tables):
        session.execute(table.delete())
    session.commit()
    session.close()
