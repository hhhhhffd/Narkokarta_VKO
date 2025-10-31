"""
Бизнес-логика модерации меток.
Используется модераторами для одобрения/отклонения меток и полицией для отметки "решено".
"""
from sqlalchemy.orm import Session
from typing import List, Optional

from ..models import Marker, MarkerStatus, ModerationLog, User
from .marker_service import get_marker_by_id


def get_pending_markers(
    db: Session,
    skip: int = 0,
    limit: int = 100
) -> List[Marker]:
    """
    Получение меток, ожидающих модерации.

    Args:
        db: Сессия БД
        skip: Пропустить N записей
        limit: Макс. количество записей

    Returns:
        Список меток со статусом NEW
    """
    return db.query(Marker).filter(
        Marker.status == MarkerStatus.NEW
    ).order_by(
        Marker.created_at.asc()  # Старые первыми
    ).offset(skip).limit(limit).all()


def approve_marker(
    db: Session,
    marker_id: int,
    moderator_id: int,
    comment: Optional[str] = None
) -> Optional[Marker]:
    """
    Одобрение метки модератором.

    Args:
        db: Сессия БД
        marker_id: ID метки
        moderator_id: ID модератора
        comment: Комментарий модератора (опционально)

    Returns:
        Обновлённая метка или None

    Процесс:
    1. Меняем статус на APPROVED
    2. Записываем лог модерации
    """
    marker = get_marker_by_id(db, marker_id)
    if not marker:
        return None

    # Обновляем статус
    marker.status = MarkerStatus.APPROVED
    db.commit()

    # Логируем действие
    log = ModerationLog(
        marker_id=marker_id,
        moderator_id=moderator_id,
        action="approved",
        comment=comment
    )
    db.add(log)
    db.commit()

    db.refresh(marker)
    return marker


def reject_marker(
    db: Session,
    marker_id: int,
    moderator_id: int,
    comment: Optional[str] = None
) -> Optional[Marker]:
    """
    Отклонение метки модератором.

    Args:
        db: Сессия БД
        marker_id: ID метки
        moderator_id: ID модератора
        comment: Причина отклонения (опционально)

    Returns:
        Обновлённая метка или None

    Процесс:
    1. Меняем статус на REJECTED
    2. Записываем лог модерации с причиной
    """
    marker = get_marker_by_id(db, marker_id)
    if not marker:
        return None

    # Обновляем статус
    marker.status = MarkerStatus.REJECTED
    db.commit()

    # Логируем действие
    log = ModerationLog(
        marker_id=marker_id,
        moderator_id=moderator_id,
        action="rejected",
        comment=comment
    )
    db.add(log)
    db.commit()

    db.refresh(marker)
    return marker


def resolve_marker(
    db: Session,
    marker_id: int,
    police_id: int,
    comment: Optional[str] = None,
    report_photo_url: Optional[str] = None
) -> Optional[Marker]:
    """
    Отметка метки как "решено" полицией.

    Args:
        db: Сессия БД
        marker_id: ID метки
        police_id: ID сотрудника полиции
        comment: Отчёт о проделанной работе
        report_photo_url: Фото отчёта (опционально)

    Returns:
        Обновлённая метка или None

    Процесс:
    1. Меняем статус на RESOLVED
    2. Записываем лог с отчётом и фото
    """
    marker = get_marker_by_id(db, marker_id)
    if not marker:
        return None

    # Обновляем статус
    marker.status = MarkerStatus.RESOLVED
    db.commit()

    # Логируем действие
    log = ModerationLog(
        marker_id=marker_id,
        moderator_id=police_id,
        action="resolved",
        comment=comment,
        report_photo_url=report_photo_url
    )
    db.add(log)
    db.commit()

    db.refresh(marker)
    return marker


def get_marker_moderation_history(db: Session, marker_id: int) -> List[ModerationLog]:
    """
    Получение истории модерации метки.

    Args:
        db: Сессия БД
        marker_id: ID метки

    Returns:
        Список логов модерации
    """
    return db.query(ModerationLog).filter(
        ModerationLog.marker_id == marker_id
    ).order_by(
        ModerationLog.created_at.desc()
    ).all()


def get_moderator_stats(db: Session, moderator_id: int) -> dict:
    """
    Получение статистики работы модератора.

    Args:
        db: Сессия БД
        moderator_id: ID модератора

    Returns:
        Словарь со статистикой
    """
    logs = db.query(ModerationLog).filter(
        ModerationLog.moderator_id == moderator_id
    ).all()

    approved = sum(1 for log in logs if log.action == "approved")
    rejected = sum(1 for log in logs if log.action == "rejected")
    resolved = sum(1 for log in logs if log.action == "resolved")

    return {
        "moderator_id": moderator_id,
        "total_actions": len(logs),
        "approved": approved,
        "rejected": rejected,
        "resolved": resolved
    }


def bulk_approve_markers(
    db: Session,
    marker_ids: List[int],
    moderator_id: int,
    comment: Optional[str] = None
) -> List[Marker]:
    """
    Массовое одобрение меток.

    Args:
        db: Сессия БД
        marker_ids: Список ID меток
        moderator_id: ID модератора
        comment: Общий комментарий

    Returns:
        Список одобренных меток
    """
    approved_markers = []

    for marker_id in marker_ids:
        marker = approve_marker(db, marker_id, moderator_id, comment)
        if marker:
            approved_markers.append(marker)

    return approved_markers
