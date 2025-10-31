"""
FastAPI Dependencies для авторизации и RBAC.

Использование в роутерах:
@router.get("/protected")
def protected_route(current_user: User = Depends(get_current_user)):
    ...

@router.get("/admin-only")
def admin_route(current_user: User = Depends(require_admin)):
    ...
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional

from ..database import get_db
from ..models import User, UserRole
from .jwt import verify_token


# Security scheme для Swagger UI
security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Извлечение текущего пользователя из JWT токена.

    Args:
        credentials: Bearer токен из заголовка Authorization
        db: Сессия БД

    Returns:
        User объект текущего пользователя

    Raises:
        HTTPException 401: Невалидный токен или пользователь не найден
    """
    token = credentials.credentials
    payload = verify_token(token, token_type="access")

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Невалидный токен авторизации",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Невалидный формат токена",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь не найден",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Пользователь деактивирован"
        )

    return user


def require_role(required_role: UserRole):
    """
    Фабрика dependency для проверки роли пользователя.

    Args:
        required_role: Требуемая роль

    Returns:
        Dependency функция

    Пример:
    @router.get("/moderators-only")
    def mod_route(user: User = Depends(require_role(UserRole.MODERATOR))):
        ...
    """
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        # Админ имеет доступ ко всему
        if current_user.role == UserRole.ADMIN:
            return current_user

        # Иерархия ролей: admin > police > moderator > user
        role_hierarchy = {
            UserRole.USER: 0,
            UserRole.MODERATOR: 1,
            UserRole.POLICE: 2,
            UserRole.ADMIN: 3
        }

        if role_hierarchy.get(current_user.role, 0) < role_hierarchy.get(required_role, 0):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Требуется роль {required_role.value} или выше"
            )

        return current_user

    return role_checker


# Готовые dependencies для частых случаев
def require_moderator(current_user: User = Depends(get_current_user)) -> User:
    """Требуется роль moderator или выше"""
    return require_role(UserRole.MODERATOR)(current_user)


def require_police(current_user: User = Depends(get_current_user)) -> User:
    """Требуется роль police или admin"""
    return require_role(UserRole.POLICE)(current_user)


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Требуется роль admin"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Требуются права администратора"
        )
    return current_user


# Optional auth - пользователь может быть не авторизован
def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Опциональная авторизация - если токен есть, проверяем, если нет - возвращаем None.

    Используется для эндпоинтов, которые работают и без авторизации,
    но могут предоставлять дополнительные данные авторизованным пользователям.
    """
    if not credentials:
        return None

    try:
        return get_current_user(credentials, db)
    except HTTPException:
        return None
