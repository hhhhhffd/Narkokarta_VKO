"""
Роутер меток: CRUD операции с фильтрацией и загрузкой фото.
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

from ..database import get_db
from ..models import User, Marker, MarkerType, MarkerColor, MarkerStatus
from ..auth.dependencies import get_current_user, get_current_user_optional
from ..services.marker_service import (
    create_marker,
    get_marker_by_id,
    get_markers,
    update_marker,
    delete_marker,
    check_duplicate_marker,
    get_markers_stats
)
from ..services.user_service import check_user_activity_limit, log_user_activity
from ..services.media_service import media_service


router = APIRouter(prefix="/markers", tags=["Markers"])


# Pydantic модели
class MarkerResponse(BaseModel):
    id: int
    title: str
    description: str | None
    address: str | None
    latitude: float
    longitude: float
    type: str
    color: str
    status: str
    photo_url: str | None
    created_by: int
    created_at: str

    class Config:
        from_attributes = True


class CreateMarkerRequest(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    type: MarkerType
    address: Optional[str] = Field(None, max_length=512)
    description: Optional[str] = Field(None, max_length=2000)
    title: Optional[str] = None
    color: Optional[MarkerColor] = None


class UpdateMarkerRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=255)
    description: Optional[str] = None
    type: Optional[MarkerType] = None
    color: Optional[MarkerColor] = None


class MarkersStatsResponse(BaseModel):
    total: int
    by_status: dict
    by_type: dict


@router.post("", response_model=MarkerResponse, status_code=status.HTTP_201_CREATED)
def create_marker_endpoint(
    request: CreateMarkerRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Создание новой метки (упрощенная версия).

    Процесс:
    1. Проверка дневного лимита пользователя
    2. Проверка на дубликаты (метка в том же месте)
    3. Автоматическое определение цвета по типу
    4. Автоматическая генерация названия если не указано
    5. Создание метки со статусом APPROVED (сразу видна всем)
    6. Логирование активности

    Требует: Bearer токен

    Пример запроса:
    ```
    POST /markers
    {
        "latitude": 55.7558,
        "longitude": 37.6173,
        "type": "den",
        "description": "Подъезд: 1\nКвартира: 15\nЭтаж: 3\nОписание: Подозрительная активность"
    }
    ```

    Пример ответа:
    ```
    {
        "id": 1,
        "title": "Притон",
        "description": null,
        "latitude": 55.7558,
        "longitude": 37.6173,
        "type": "den",
        "color": "red",
        "status": "approved",
        "photo_url": null,
        "created_by": 1,
        "created_at": "2025-10-30T10:00:00"
    }
    ```
    """
    # Проверка дневного лимита
    if not check_user_activity_limit(db, current_user.id, "create_marker"):
        from ..config import settings
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Превышен дневной лимит ({settings.MAX_MARKERS_PER_USER_PER_DAY} меток в день)"
        )

    # Проверка на дубликаты
    if check_duplicate_marker(db, request.latitude, request.longitude, current_user.id):
        from ..config import settings
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"У вас уже есть метка в радиусе {settings.MIN_DISTANCE_BETWEEN_MARKERS_METERS}м от этой точки"
        )

    # Автоматическое определение цвета по типу
    type_to_color = {
        MarkerType.DEN: MarkerColor.RED,
        MarkerType.AD: MarkerColor.ORANGE,
        MarkerType.COURIER: MarkerColor.YELLOW,
        MarkerType.USER: MarkerColor.GREEN,
        MarkerType.TRASH: MarkerColor.WHITE
    }
    color = request.color if request.color else type_to_color.get(request.type, MarkerColor.YELLOW)

    # Автоматическая генерация названия если не указано
    type_to_title = {
        MarkerType.DEN: "Притон",
        MarkerType.AD: "Реклама наркотиков",
        MarkerType.COURIER: "Место встречи с курьером",
        MarkerType.USER: "Место употребления",
        MarkerType.TRASH: "Мусор от употребления"
    }
    title = request.title if request.title else type_to_title.get(request.type, "Метка")

    # Создание метки
    marker = create_marker(
        db=db,
        user_id=current_user.id,
        title=title,
        description=request.description,
        latitude=request.latitude,
        longitude=request.longitude,
        marker_type=request.type,
        color=color,
        address=request.address
    )

    # Логирование активности
    log_user_activity(db, current_user.id, "create_marker")

    return MarkerResponse(
        id=marker.id,
        title=marker.title,
        description=marker.description,
        address=marker.address,
        latitude=marker.latitude,
        longitude=marker.longitude,
        type=marker.type.value,
        color=marker.color.value,
        status=marker.status.value,
        photo_url=marker.photo_url,
        created_by=marker.created_by,
        created_at=marker.created_at.isoformat() if marker.created_at else ""
    )


@router.post("/{marker_id}/photo", response_model=MarkerResponse)
async def upload_marker_photo(
    marker_id: int,
    photo: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Загрузка фото для метки.

    Требует: Bearer токен, владелец метки или moderator+

    Пример запроса:
    ```
    POST /markers/1/photo
    Content-Type: multipart/form-data
    photo: <file>
    ```
    """
    # Получение метки
    marker = get_marker_by_id(db, marker_id)
    if not marker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Метка не найдена"
        )

    # Проверка прав (владелец или модератор+)
    if marker.created_by != current_user.id and current_user.role.value not in ["moderator", "police", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав"
        )

    # Валидация файла
    file_size = 0
    file_content = await photo.read()
    file_size = len(file_content)
    await photo.seek(0)

    is_valid, error_msg = media_service.validate_file(photo.filename, file_size)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )

    # Сохранение файла
    filename = media_service.generate_filename(photo.filename)
    file_url = media_service.save_file(photo.file, filename)

    # Обновление метки
    updated_marker = update_marker(db, marker_id, photo_url=file_url)

    return MarkerResponse(
        id=updated_marker.id,
        title=updated_marker.title,
        description=updated_marker.description,
        latitude=updated_marker.latitude,
        longitude=updated_marker.longitude,
        type=updated_marker.type.value,
        color=updated_marker.color.value,
        status=updated_marker.status.value,
        photo_url=updated_marker.photo_url,
        created_by=updated_marker.created_by,
        created_at=updated_marker.created_at.isoformat() if updated_marker.created_at else ""
    )


@router.get("", response_model=List[MarkerResponse])
def get_markers_endpoint(
    skip: int = 0,
    limit: int = 100,
    type: Optional[MarkerType] = None,
    color: Optional[MarkerColor] = None,
    status: Optional[MarkerStatus] = None,
    center_lat: Optional[float] = None,
    center_lon: Optional[float] = None,
    radius_km: Optional[float] = None,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Получение списка меток с фильтрацией.

    Фильтры:
    - type: тип метки (den, ad, courier, user, trash)
    - color: цвет (red, orange, yellow, green, white)
    - status: статус (new, approved, rejected, resolved)
    - center_lat, center_lon, radius_km: геолокация

    Пагинация:
    - skip: пропустить N записей
    - limit: макс. количество (по умолчанию 100)

    Авторизация: опциональная
    - Все метки общедоступны (всегда APPROVED)

    Пример запроса:
    ```
    GET /markers?type=den&color=red&center_lat=55.7558&center_lon=37.6173&radius_km=5
    ```

    Пример ответа:
    ```
    [
        {
            "id": 1,
            "title": "Подозрительная активность",
            ...
        }
    ]
    ```
    """
    markers = get_markers(
        db=db,
        skip=skip,
        limit=limit,
        marker_type=type,
        color=color,
        status=status,
        center_lat=center_lat,
        center_lon=center_lon,
        radius_km=radius_km
    )

    return [
        MarkerResponse(
            id=m.id,
            title=m.title,
            description=m.description,
            address=m.address,
            latitude=m.latitude,
            longitude=m.longitude,
            type=m.type.value,
            color=m.color.value,
            status=m.status.value,
            photo_url=m.photo_url,
            created_by=m.created_by,
            created_at=m.created_at.isoformat() if m.created_at else ""
        )
        for m in markers
    ]


@router.get("/stats", response_model=MarkersStatsResponse)
def get_markers_stats_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Получение статистики по меткам.

    Требует: Bearer токен

    Пример ответа:
    ```
    {
        "total": 150,
        "by_status": {
            "new": 10,
            "approved": 120,
            "rejected": 15,
            "resolved": 5
        },
        "by_type": {
            "den": 50,
            "ad": 30,
            "courier": 20,
            "user": 40,
            "trash": 10
        }
    }
    ```
    """
    stats = get_markers_stats(db)
    return MarkersStatsResponse(**stats)


@router.get("/{marker_id}", response_model=MarkerResponse)
def get_marker_endpoint(
    marker_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Получение метки по ID.

    Авторизация: опциональная
    """
    marker = get_marker_by_id(db, marker_id)

    if not marker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Метка не найдена"
        )

    return MarkerResponse(
        id=marker.id,
        title=marker.title,
        description=marker.description,
        address=marker.address,
        latitude=marker.latitude,
        longitude=marker.longitude,
        type=marker.type.value,
        color=marker.color.value,
        status=marker.status.value,
        photo_url=marker.photo_url,
        created_by=marker.created_by,
        created_at=marker.created_at.isoformat() if marker.created_at else ""
    )


@router.patch("/{marker_id}", response_model=MarkerResponse)
def update_marker_endpoint(
    marker_id: int,
    request: UpdateMarkerRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Обновление метки.

    Требует: Bearer токен, владелец метки

    Можно изменить:
    - title, description, type, color

    Нельзя изменить:
    - latitude, longitude (создайте новую метку)
    - status (используйте модерацию)
    """
    marker = get_marker_by_id(db, marker_id)

    if not marker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Метка не найдена"
        )

    # Проверка прав (только владелец)
    if marker.created_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Вы можете редактировать только свои метки"
        )

    updated_marker = update_marker(
        db=db,
        marker_id=marker_id,
        title=request.title,
        description=request.description,
        marker_type=request.type,
        color=request.color
    )

    return MarkerResponse(
        id=updated_marker.id,
        title=updated_marker.title,
        description=updated_marker.description,
        latitude=updated_marker.latitude,
        longitude=updated_marker.longitude,
        type=updated_marker.type.value,
        color=updated_marker.color.value,
        status=updated_marker.status.value,
        photo_url=updated_marker.photo_url,
        created_by=updated_marker.created_by,
        created_at=updated_marker.created_at.isoformat() if updated_marker.created_at else ""
    )


@router.delete("/{marker_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_marker_endpoint(
    marker_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Удаление метки.

    Требует: Bearer токен, владелец или moderator+
    """
    marker = get_marker_by_id(db, marker_id)

    if not marker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Метка не найдена"
        )

    # Проверка прав (владелец или модератор+)
    if marker.created_by != current_user.id and current_user.role.value not in ["moderator", "police", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав"
        )

    # Удаление фото если есть
    if marker.photo_url:
        media_service.delete_file(marker.photo_url)

    delete_marker(db, marker_id)
    return None
