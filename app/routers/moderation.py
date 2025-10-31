"""
Роутер модерации: одобрение/отклонение меток, полицейские отчёты.
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List

from ..database import get_db
from ..models import User, Marker
from ..auth.dependencies import get_current_user, require_moderator, require_police
from ..services.moderation_service import (
    get_pending_markers,
    approve_marker,
    reject_marker,
    resolve_marker,
    get_marker_moderation_history,
    get_moderator_stats
)
from ..services.marker_service import get_marker_by_id
from ..services.media_service import media_service


router = APIRouter(prefix="/moderation", tags=["Moderation"])


# Pydantic модели
class MarkerResponse(BaseModel):
    id: int
    title: str
    description: str | None
    latitude: float
    longitude: float
    type: str
    color: str
    status: str
    photo_url: str | None
    created_by: int
    created_at: str


class ModerationActionRequest(BaseModel):
    comment: Optional[str] = None


class ResolveMarkerRequest(BaseModel):
    comment: Optional[str] = None


class ModerationLogResponse(BaseModel):
    id: int
    marker_id: int
    moderator_id: int
    action: str
    comment: str | None
    report_photo_url: str | None
    created_at: str


class ModeratorStatsResponse(BaseModel):
    moderator_id: int
    total_actions: int
    approved: int
    rejected: int
    resolved: int


@router.get("/pending", response_model=List[MarkerResponse])
def get_pending_markers_endpoint(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_moderator)
):
    """
    Получение меток, ожидающих модерации.

    Требует: роль moderator или выше

    Пример запроса:
    ```
    GET /moderation/pending?skip=0&limit=10
    ```

    Пример ответа:
    ```
    [
        {
            "id": 1,
            "title": "Подозрительная активность",
            "status": "new",
            ...
        }
    ]
    ```
    """
    markers = get_pending_markers(db, skip, limit)

    return [
        MarkerResponse(
            id=m.id,
            title=m.title,
            description=m.description,
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


@router.post("/{marker_id}/approve", response_model=MarkerResponse)
def approve_marker_endpoint(
    marker_id: int,
    request: ModerationActionRequest,
    current_user: User = Depends(require_moderator),
    db: Session = Depends(get_db)
):
    """
    Одобрение метки модератором.

    Требует: роль moderator или выше

    Процесс:
    1. Метка переходит в статус APPROVED
    2. Становится видимой на карте
    3. Действие логируется

    Пример запроса:
    ```
    POST /moderation/1/approve
    {
        "comment": "Проверено, информация достоверна"
    }
    ```
    """
    marker = approve_marker(
        db=db,
        marker_id=marker_id,
        moderator_id=current_user.id,
        comment=request.comment
    )

    if not marker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Метка не найдена"
        )

    return MarkerResponse(
        id=marker.id,
        title=marker.title,
        description=marker.description,
        latitude=marker.latitude,
        longitude=marker.longitude,
        type=marker.type.value,
        color=marker.color.value,
        status=marker.status.value,
        photo_url=marker.photo_url,
        created_by=marker.created_by,
        created_at=marker.created_at.isoformat() if marker.created_at else ""
    )


@router.post("/{marker_id}/reject", response_model=MarkerResponse)
def reject_marker_endpoint(
    marker_id: int,
    request: ModerationActionRequest,
    current_user: User = Depends(require_moderator),
    db: Session = Depends(get_db)
):
    """
    Отклонение метки модератором.

    Требует: роль moderator или выше

    Процесс:
    1. Метка переходит в статус REJECTED
    2. Не отображается на карте
    3. Действие логируется с причиной

    Пример запроса:
    ```
    POST /moderation/1/reject
    {
        "comment": "Недостоверная информация"
    }
    ```
    """
    marker = reject_marker(
        db=db,
        marker_id=marker_id,
        moderator_id=current_user.id,
        comment=request.comment
    )

    if not marker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Метка не найдена"
        )

    return MarkerResponse(
        id=marker.id,
        title=marker.title,
        description=marker.description,
        latitude=marker.latitude,
        longitude=marker.longitude,
        type=marker.type.value,
        color=marker.color.value,
        status=marker.status.value,
        photo_url=marker.photo_url,
        created_by=marker.created_by,
        created_at=marker.created_at.isoformat() if marker.created_at else ""
    )


@router.post("/{marker_id}/resolve", response_model=MarkerResponse)
async def resolve_marker_endpoint(
    marker_id: int,
    comment: Optional[str] = None,
    report_photo: Optional[UploadFile] = File(None),
    current_user: User = Depends(require_police),
    db: Session = Depends(get_db)
):
    """
    Отметка метки как "решено" полицией.

    Требует: роль police или admin

    Процесс:
    1. Метка переходит в статус RESOLVED
    2. Добавляется отчёт о проделанной работе
    3. Опционально: фото отчёта

    Пример запроса:
    ```
    POST /moderation/1/resolve
    Content-Type: multipart/form-data
    comment: "Проведён рейд, притон ликвидирован"
    report_photo: <file>
    ```
    """
    # Обработка фото отчёта
    report_photo_url = None
    if report_photo:
        file_content = await report_photo.read()
        file_size = len(file_content)
        await report_photo.seek(0)

        is_valid, error_msg = media_service.validate_file(report_photo.filename, file_size)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )

        filename = media_service.generate_filename(report_photo.filename)
        report_photo_url = media_service.save_file(report_photo.file, filename)

    marker = resolve_marker(
        db=db,
        marker_id=marker_id,
        police_id=current_user.id,
        comment=comment,
        report_photo_url=report_photo_url
    )

    if not marker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Метка не найдена"
        )

    return MarkerResponse(
        id=marker.id,
        title=marker.title,
        description=marker.description,
        latitude=marker.latitude,
        longitude=marker.longitude,
        type=marker.type.value,
        color=marker.color.value,
        status=marker.status.value,
        photo_url=marker.photo_url,
        created_by=marker.created_by,
        created_at=marker.created_at.isoformat() if marker.created_at else ""
    )


@router.get("/{marker_id}/history", response_model=List[ModerationLogResponse])
def get_moderation_history_endpoint(
    marker_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_moderator)
):
    """
    Получение истории модерации метки.

    Требует: роль moderator или выше

    Пример ответа:
    ```
    [
        {
            "id": 1,
            "marker_id": 1,
            "moderator_id": 2,
            "action": "approved",
            "comment": "Проверено",
            "report_photo_url": null,
            "created_at": "2025-10-30T10:00:00"
        }
    ]
    ```
    """
    logs = get_marker_moderation_history(db, marker_id)

    return [
        ModerationLogResponse(
            id=log.id,
            marker_id=log.marker_id,
            moderator_id=log.moderator_id,
            action=log.action,
            comment=log.comment,
            report_photo_url=log.report_photo_url,
            created_at=log.created_at.isoformat() if log.created_at else ""
        )
        for log in logs
    ]


@router.get("/stats/me", response_model=ModeratorStatsResponse)
def get_my_moderator_stats_endpoint(
    current_user: User = Depends(require_moderator),
    db: Session = Depends(get_db)
):
    """
    Получение статистики работы текущего модератора.

    Требует: роль moderator или выше

    Пример ответа:
    ```
    {
        "moderator_id": 2,
        "total_actions": 50,
        "approved": 40,
        "rejected": 8,
        "resolved": 2
    }
    ```
    """
    stats = get_moderator_stats(db, current_user.id)
    return ModeratorStatsResponse(**stats)
