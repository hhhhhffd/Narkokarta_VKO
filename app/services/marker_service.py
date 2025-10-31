"""
Бизнес-логика работы с маркерами на карте.
Включает фильтрацию по геолокации, типу, статусу и дате.
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from typing import List, Optional
from datetime import datetime, timedelta
from geopy.distance import geodesic

from ..models import Marker, MarkerType, MarkerColor, MarkerStatus, User
from ..config import settings


def create_marker(
    db: Session,
    user_id: int,
    title: str,
    description: Optional[str],
    latitude: float,
    longitude: float,
    marker_type: MarkerType,
    color: MarkerColor,
    address: Optional[str] = None,
    photo_url: Optional[str] = None
) -> Marker:
    """
    Создание новой метки.

    Args:
        db: Сессия БД
        user_id: ID создателя
        title: Название метки
        description: Описание
        latitude: Широта
        longitude: Долгота
        marker_type: Тип метки
        color: Цвет метки
        address: Адрес (опционально)
        photo_url: URL фото (опционально)

    Returns:
        Созданный маркер

    Примечание:
    - Все новые метки создаются со статусом APPROVED
    - Сразу отображаются на карте без модерации
    """
    marker = Marker(
        title=title,
        description=description,
        address=address,
        latitude=latitude,
        longitude=longitude,
        type=marker_type,
        color=color,
        status=MarkerStatus.APPROVED,  # Метки сразу одобрены
        photo_url=photo_url,
        created_by=user_id
    )

    db.add(marker)
    db.commit()
    db.refresh(marker)
    return marker


def get_marker_by_id(db: Session, marker_id: int) -> Optional[Marker]:
    """Получение метки по ID"""
    return db.query(Marker).filter(Marker.id == marker_id).first()


def get_markers(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    marker_type: Optional[MarkerType] = None,
    color: Optional[MarkerColor] = None,
    status: Optional[MarkerStatus] = None,
    created_by: Optional[int] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    center_lat: Optional[float] = None,
    center_lon: Optional[float] = None,
    radius_km: Optional[float] = None
) -> List[Marker]:
    """
    Получение меток с фильтрацией.

    Args:
        db: Сессия БД
        skip: Пропустить N записей (пагинация)
        limit: Макс. количество записей
        marker_type: Фильтр по типу
        color: Фильтр по цвету
        status: Фильтр по статусу
        created_by: Фильтр по создателю
        from_date: Фильтр по дате создания (с)
        to_date: Фильтр по дате создания (до)
        center_lat: Широта центра для радиуса
        center_lon: Долгота центра для радиуса
        radius_km: Радиус поиска в километрах

    Returns:
        Список меток

    Примеры фильтрации:
    - Все одобренные метки: status=MarkerStatus.APPROVED
    - Метки в радиусе 5км: center_lat=55.75, center_lon=37.61, radius_km=5
    - Метки за последнюю неделю: from_date=datetime.now() - timedelta(days=7)
    """
    query = db.query(Marker)

    # Фильтры
    if marker_type:
        query = query.filter(Marker.type == marker_type)

    if color:
        query = query.filter(Marker.color == color)

    if status:
        query = query.filter(Marker.status == status)

    if created_by:
        query = query.filter(Marker.created_by == created_by)

    if from_date:
        query = query.filter(Marker.created_at >= from_date)

    if to_date:
        query = query.filter(Marker.created_at <= to_date)

    # Сортировка по дате (новые первыми)
    query = query.order_by(Marker.created_at.desc())

    # Получаем все результаты для геофильтрации
    markers = query.all()

    # Фильтрация по радиусу (если указан)
    if center_lat is not None and center_lon is not None and radius_km is not None:
        center = (center_lat, center_lon)
        markers = [
            m for m in markers
            if geodesic(center, (m.latitude, m.longitude)).kilometers <= radius_km
        ]

    # Пагинация после геофильтрации
    return markers[skip:skip + limit]


def update_marker(
    db: Session,
    marker_id: int,
    title: Optional[str] = None,
    description: Optional[str] = None,
    marker_type: Optional[MarkerType] = None,
    color: Optional[MarkerColor] = None,
    photo_url: Optional[str] = None
) -> Optional[Marker]:
    """
    Обновление метки (частичное).

    Args:
        db: Сессия БД
        marker_id: ID метки
        title: Новое название (опционально)
        description: Новое описание (опционально)
        marker_type: Новый тип (опционально)
        color: Новый цвет (опционально)
        photo_url: Новое фото (опционально)

    Returns:
        Обновлённая метка или None

    Примечание:
    - Геолокация не может быть изменена (создайте новую метку)
    - Статус изменяется только через модерацию
    """
    marker = get_marker_by_id(db, marker_id)
    if not marker:
        return None

    if title is not None:
        marker.title = title

    if description is not None:
        marker.description = description

    if marker_type is not None:
        marker.type = marker_type

    if color is not None:
        marker.color = color

    if photo_url is not None:
        marker.photo_url = photo_url

    db.commit()
    db.refresh(marker)
    return marker


def delete_marker(db: Session, marker_id: int) -> bool:
    """
    Удаление метки.

    Args:
        db: Сессия БД
        marker_id: ID метки

    Returns:
        True если удалена, False если не найдена
    """
    marker = get_marker_by_id(db, marker_id)
    if not marker:
        return False

    db.delete(marker)
    db.commit()
    return True


def check_duplicate_marker(
    db: Session,
    latitude: float,
    longitude: float,
    user_id: int,
    min_distance_meters: Optional[float] = None
) -> bool:
    """
    Проверка на дублирование меток (anti-spam).

    Args:
        db: Сессия БД
        latitude: Широта новой метки
        longitude: Долгота новой метки
        user_id: ID пользователя
        min_distance_meters: Минимальное расстояние в метрах

    Returns:
        True если дубликат найден, False если нет

    Проверяет:
    - Есть ли метки этого пользователя в радиусе MIN_DISTANCE_BETWEEN_MARKERS_METERS
    """
    if min_distance_meters is None:
        min_distance_meters = settings.MIN_DISTANCE_BETWEEN_MARKERS_METERS

    # Получаем все метки пользователя
    user_markers = db.query(Marker).filter(Marker.created_by == user_id).all()

    new_point = (latitude, longitude)

    for marker in user_markers:
        marker_point = (marker.latitude, marker.longitude)
        distance_m = geodesic(new_point, marker_point).meters

        if distance_m < min_distance_meters:
            return True

    return False


def get_markers_stats(db: Session) -> dict:
    """
    Получение общей статистики по меткам.

    Returns:
        Словарь со статистикой
    """
    total = db.query(Marker).count()
    new = db.query(Marker).filter(Marker.status == MarkerStatus.NEW).count()
    approved = db.query(Marker).filter(Marker.status == MarkerStatus.APPROVED).count()
    rejected = db.query(Marker).filter(Marker.status == MarkerStatus.REJECTED).count()
    resolved = db.query(Marker).filter(Marker.status == MarkerStatus.RESOLVED).count()

    # Статистика по типам
    by_type = {}
    for marker_type in MarkerType:
        count = db.query(Marker).filter(Marker.type == marker_type).count()
        by_type[marker_type.value] = count

    return {
        "total": total,
        "by_status": {
            "new": new,
            "approved": approved,
            "rejected": rejected,
            "resolved": resolved
        },
        "by_type": by_type
    }
