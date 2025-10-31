"""
Бизнес-логика работы с пользователями.
Изолирована от FastAPI - может использоваться в любом окружении.
"""
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta, timezone

from ..models import User, UserRole, UserActivity
from ..config import settings


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    """Получение пользователя по ID"""
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_phone(db: Session, phone: str) -> Optional[User]:
    """Получение пользователя по номеру телефона"""
    return db.query(User).filter(User.phone == phone).first()


def get_all_users(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    role: Optional[UserRole] = None,
    is_active: Optional[bool] = None
) -> List[User]:
    """
    Получение списка пользователей с фильтрацией.

    Args:
        db: Сессия БД
        skip: Пропустить N записей (для пагинации)
        limit: Макс. количество записей
        role: Фильтр по роли
        is_active: Фильтр по статусу активности

    Returns:
        Список пользователей
    """
    query = db.query(User)

    if role:
        query = query.filter(User.role == role)

    if is_active is not None:
        query = query.filter(User.is_active == is_active)

    return query.offset(skip).limit(limit).all()


def update_user(
    db: Session,
    user_id: int,
    full_name: Optional[str] = None,
    role: Optional[UserRole] = None,
    is_active: Optional[bool] = None
) -> Optional[User]:
    """
    Обновление данных пользователя.

    Args:
        db: Сессия БД
        user_id: ID пользователя
        full_name: Новое имя (опционально)
        role: Новая роль (опционально)
        is_active: Новый статус активности (опционально)

    Returns:
        Обновлённый пользователь или None
    """
    user = get_user_by_id(db, user_id)
    if not user:
        return None

    if full_name is not None:
        user.full_name = full_name

    if role is not None:
        user.role = role

    if is_active is not None:
        user.is_active = is_active

    db.commit()
    db.refresh(user)
    return user


def delete_user(db: Session, user_id: int) -> bool:
    """
    Удаление пользователя.

    Args:
        db: Сессия БД
        user_id: ID пользователя

    Returns:
        True если удалён, False если не найден
    """
    user = get_user_by_id(db, user_id)
    if not user:
        return False

    db.delete(user)
    db.commit()
    return True


def check_user_activity_limit(db: Session, user_id: int, action: str = "create_marker") -> bool:
    """
    Проверка лимита активности пользователя для anti-spam.

    Args:
        db: Сессия БД
        user_id: ID пользователя
        action: Тип действия

    Returns:
        True если лимит не превышен, False если превышен

    Проверяет:
    - Количество действий за последние 24 часа
    """
    since = datetime.now(timezone.utc) - timedelta(days=1)

    count = db.query(UserActivity).filter(
        UserActivity.user_id == user_id,
        UserActivity.action == action,
        UserActivity.created_at >= since
    ).count()

    return count < settings.MAX_MARKERS_PER_USER_PER_DAY


def log_user_activity(db: Session, user_id: int, action: str):
    """
    Логирование активности пользователя.

    Args:
        db: Сессия БД
        user_id: ID пользователя
        action: Тип действия
    """
    activity = UserActivity(user_id=user_id, action=action)
    db.add(activity)
    db.commit()


def get_user_stats(db: Session, user_id: int) -> dict:
    """
    Получение статистики пользователя.

    Args:
        db: Сессия БД
        user_id: ID пользователя

    Returns:
        Словарь со статистикой
    """
    user = get_user_by_id(db, user_id)
    if not user:
        return {}

    total_markers = len(user.markers)
    today = datetime.now(timezone.utc).date()
    today_activities = [a for a in user.activities if a.created_at.date() == today]

    return {
        "user_id": user_id,
        "phone": user.phone,
        "role": user.role.value,
        "total_markers": total_markers,
        "today_activities": len(today_activities),
        "daily_limit_remaining": settings.MAX_MARKERS_PER_USER_PER_DAY - len(today_activities)
    }
