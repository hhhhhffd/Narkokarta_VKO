"""
Настройка базы данных.
Поддерживает SQLite (для разработки) и PostgreSQL (для продакшена).
Использует SQLAlchemy 2.0 async API для совместимости с FastAPI.
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
from .config import settings

# Определяем движок БД
# Для SQLite добавляем check_same_thread=False
if settings.DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=settings.DEBUG  # SQL логирование в debug режиме
    )
else:
    # PostgreSQL или другие БД
    engine = create_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,  # Проверка соединения перед использованием
        pool_size=10,
        max_overflow=20
    )

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class для моделей
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Dependency для получения сессии БД в роутерах.

    Использование:
    @app.get("/")
    def read_root(db: Session = Depends(get_db)):
        ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Создание всех таблиц.
    Вызывается при старте приложения или через скрипт init_db.py
    """
    Base.metadata.create_all(bind=engine)
