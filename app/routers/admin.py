"""
Роутер администрирования: управление пользователями и ролями.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional

from ..database import get_db
from ..models import User, UserRole
from ..auth.dependencies import get_current_user, require_admin
from ..services.user_service import (
    get_all_users,
    get_user_by_id,
    update_user,
    delete_user,
    get_user_stats
)


router = APIRouter(prefix="/admin", tags=["Administration"])


# Pydantic модели
class UserResponse(BaseModel):
    id: int
    phone: str
    full_name: str | None
    role: str
    is_active: bool
    created_at: str


class UpdateUserAdminRequest(BaseModel):
    full_name: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


@router.get("/users", response_model=List[UserResponse])
def get_all_users_endpoint(
    skip: int = 0,
    limit: int = 100,
    role: Optional[UserRole] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Получение списка всех пользователей с фильтрацией.

    Требует: роль admin

    Фильтры:
    - role: фильтр по роли
    - is_active: фильтр по статусу

    Пример запроса:
    ```
    GET /admin/users?role=moderator&is_active=true
    ```

    Пример ответа:
    ```
    [
        {
            "id": 1,
            "phone": "+79991234567",
            "full_name": "Иван Иванов",
            "role": "user",
            "is_active": true,
            "created_at": "2025-10-30T10:00:00"
        }
    ]
    ```
    """
    users = get_all_users(
        db=db,
        skip=skip,
        limit=limit,
        role=role,
        is_active=is_active
    )

    return [
        UserResponse(
            id=u.id,
            phone=u.phone,
            full_name=u.full_name,
            role=u.role.value,
            is_active=u.is_active,
            created_at=u.created_at.isoformat() if u.created_at else ""
        )
        for u in users
    ]


@router.get("/users/{user_id}", response_model=UserResponse)
def get_user_by_id_admin_endpoint(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Получение пользователя по ID.

    Требует: роль admin
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


@router.patch("/users/{user_id}", response_model=UserResponse)
def update_user_admin_endpoint(
    user_id: int,
    request: UpdateUserAdminRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Обновление пользователя администратором.

    Требует: роль admin

    Можно изменить:
    - full_name: имя
    - role: роль (user, moderator, police, admin)
    - is_active: статус активности

    Пример запроса:
    ```
    PATCH /admin/users/1
    {
        "role": "moderator",
        "is_active": true
    }
    ```
    """
    # Проверка существования пользователя
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден"
        )

    # Нельзя изменять самого себя (защита от блокировки)
    if user_id == current_user.id and request.is_active is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нельзя деактивировать самого себя"
        )

    # Обновление
    updated_user = update_user(
        db=db,
        user_id=user_id,
        full_name=request.full_name,
        role=request.role,
        is_active=request.is_active
    )

    return UserResponse(
        id=updated_user.id,
        phone=updated_user.phone,
        full_name=updated_user.full_name,
        role=updated_user.role.value,
        is_active=updated_user.is_active,
        created_at=updated_user.created_at.isoformat() if updated_user.created_at else ""
    )


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user_admin_endpoint(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Удаление пользователя.

    Требует: роль admin

    ВНИМАНИЕ: Удаление пользователя также удалит все его метки!

    Пример запроса:
    ```
    DELETE /admin/users/1
    ```
    """
    # Нельзя удалять самого себя
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нельзя удалить самого себя"
        )

    success = delete_user(db, user_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден"
        )

    return None


@router.get("/users/{user_id}/stats")
def get_user_stats_admin_endpoint(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Получение статистики пользователя.

    Требует: роль admin

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
    stats = get_user_stats(db, user_id)

    if not stats:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден"
        )

    return stats
