"""
SQLAlchemy модели для всех сущностей системы.

Models:
- User: пользователи с RBAC ролями
- OTPCode: временные OTP коды для авторизации
- Marker: метки на карте
- ModerationLog: логи модерации
- UserActivity: активность пользователей для anti-spam
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Enum, ForeignKey, Boolean, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum

from .database import Base


# Enums
class UserRole(str, enum.Enum):
    """Роли пользователей с разными уровнями доступа"""
    USER = "user"           # Обычный пользователь - может создавать метки
    MODERATOR = "moderator" # Модератор - может подтверждать/удалять метки
    POLICE = "police"       # Полиция - может отмечать resolved + добавлять отчёты
    ADMIN = "admin"         # Админ - полный доступ ко всему


class MarkerType(str, enum.Enum):
    """Типы меток на карте"""
    DEN = "den"           # Притон
    AD = "ad"             # Реклама наркотиков
    COURIER = "courier"   # Место встречи с курьером
    USER = "user"         # Место употребления
    TRASH = "trash"       # Мусор от употребления (шприцы и т.д.)


class MarkerColor(str, enum.Enum):
    """Цветовая кодировка меток по степени опасности"""
    RED = "red"           # Критично
    ORANGE = "orange"     # Высокая опасность
    YELLOW = "yellow"     # Средняя опасность
    GREEN = "green"       # Низкая опасность
    WHITE = "white"       # Нейтрально


class MarkerStatus(str, enum.Enum):
    """Статус модерации метки"""
    NEW = "new"           # Ожидает модерации
    APPROVED = "approved" # Одобрено модератором
    REJECTED = "rejected" # Отклонено модератором
    RESOLVED = "resolved" # Решено полицией


# Models
class User(Base):
    """
    Модель пользователя с телефонной авторизацией.
    Роль определяет доступ к функциям через RBAC.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String(20), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=True)
    role = Column(Enum(UserRole), default=UserRole.USER, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    markers = relationship("Marker", back_populates="creator", cascade="all, delete-orphan")
    activities = relationship("UserActivity", back_populates="user", cascade="all, delete-orphan")


class OTPCode(Base):
    """
    Временные OTP коды для авторизации по телефону.
    Коды истекают через OTP_EXPIRE_MINUTES.
    """
    __tablename__ = "otp_codes"

    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String(20), index=True, nullable=False)
    code = Column(String(10), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_used = Column(Boolean, default=False, nullable=False)


class Marker(Base):
    """
    Метка на карте с геолокацией и метаданными.
    Все метки проходят модерацию перед отображением.
    """
    __tablename__ = "markers"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    address = Column(String(512), nullable=True)  # Адрес или координаты в текстовом виде
    latitude = Column(Float, nullable=False, index=True)
    longitude = Column(Float, nullable=False, index=True)
    type = Column(Enum(MarkerType), nullable=False, index=True)
    color = Column(Enum(MarkerColor), default=MarkerColor.YELLOW, nullable=False)
    status = Column(Enum(MarkerStatus), default=MarkerStatus.NEW, nullable=False, index=True)
    photo_url = Column(String(512), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Foreign keys
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Relationships
    creator = relationship("User", back_populates="markers")
    moderation_logs = relationship("ModerationLog", back_populates="marker", cascade="all, delete-orphan")


class ModerationLog(Base):
    """
    Логи модерации для аудита действий модераторов/полиции.
    Фиксирует кто, когда и что сделал с меткой.
    """
    __tablename__ = "moderation_logs"

    id = Column(Integer, primary_key=True, index=True)
    marker_id = Column(Integer, ForeignKey("markers.id"), nullable=False)
    moderator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(String(50), nullable=False)  # approved, rejected, resolved
    comment = Column(Text, nullable=True)
    report_photo_url = Column(String(512), nullable=True)  # Для полиции - фото отчёта
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    marker = relationship("Marker", back_populates="moderation_logs")
    moderator = relationship("User")


class UserActivity(Base):
    """
    Трекинг активности пользователей для anti-spam механизмов.
    Ограничивает количество меток от одного пользователя за день.
    """
    __tablename__ = "user_activities"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(String(50), nullable=False)  # create_marker, update_marker
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Relationships
    user = relationship("User", back_populates="activities")
