"""
Роутер пользователей: профиль, статистика.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from ..database import get_db
from ..models import User, UserRole
from ..auth.dependencies import get_current_user, require_admin
from ..services.user_service import (
    get_user_by_id,
    get_user_stats,
    update_user
)


router = APIRouter(prefix="/users", tags=["Users"])


# Pydantic модели
class UserResponse(BaseModel):
    id: int
    phone: str
    full_name: str | None
    role: str
    is_active: bool
    created_at: str

    class Config:
        from_attributes = True


class UserStatsResponse(BaseModel):
    user_id: int
    phone: str
    role: str
    total_markers: int
    today_activities: int
    daily_limit_remaining: int


class UpdateUserRequest(BaseModel):
    full_name: Optional[str] = None


@router.get("/me", response_model=UserResponse)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """
    Получение профиля текущего пользователя.

    Требует: Bearer токен

    Пример запроса:
    ```
    GET /users/me
    Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
    ```

    Пример ответа:
    ```
    {
        "id": 1,
        "phone": "+79991234567",
        "full_name": "Иван Иванов",
        "role": "user",
        "is_active": true,
        "created_at": "2025-10-30T10:00:00"
    }
    ```
    """
    return UserResponse(
        id=current_user.id,
        phone=current_user.phone,
        full_name=current_user.full_name,
        role=current_user.role.value,
        is_active=current_user.is_active,
        created_at=current_user.created_at.isoformat() if current_user.created_at else ""
    )


@router.get("/me/stats", response_model=UserStatsResponse)
def get_current_user_stats_endpoint(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Получение статистики текущего пользователя.

    Показывает:
    - Общее количество созданных меток
    - Активность за сегодня
    - Оставшийся дневной лимит

    Требует: Bearer токен

    Пример ответа:
    ```
    {
        "user_id": 1,
        "phone": "+79991234567",
        "role": "user",
        "total_markers": 15,
        "today_activities": 3,
        "daily_limit_remaining": 7
    }
    ```
    """
    stats = get_user_stats(db, current_user.id)
    return UserStatsResponse(**stats)


@router.patch("/me", response_model=UserResponse)
def update_current_user_profile(
    request: UpdateUserRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Обновление профиля текущего пользователя.

    Можно изменить:
    - full_name (имя)

    Требует: Bearer токен

    Пример запроса:
    ```
    PATCH /users/me
    {
        "full_name": "Иван Иванов"
    }
    ```
    """
    updated_user = update_user(
        db,
        current_user.id,
        full_name=request.full_name
    )

    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден"
        )

    return UserResponse(
        id=updated_user.id,
        phone=updated_user.phone,
        full_name=updated_user.full_name,
        role=updated_user.role.value,
        is_active=updated_user.is_active,
        created_at=updated_user.created_at.isoformat() if updated_user.created_at else ""
    )


@router.get("/{user_id}", response_model=UserResponse)
def get_user_by_id_endpoint(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Получение пользователя по ID.

    Требует: роль admin

    Пример запроса:
    ```
    GET /users/123
    ```
    """
    user = get_user_by_id(db, user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден"
        )

    return UserResponse(
        id=user.id,
        phone=user.phone,
        full_name=user.full_name,
        role=user.role.value,
        is_active=user.is_active,
        created_at=user.created_at.isoformat() if user.created_at else ""
    )
