"""
JWT токены для авторизации.
После успешной OTP верификации выдаются access и refresh токены.
Access токен живёт короткое время (по умолчанию 60 мин), refresh - дольше (30 дней).
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from ..config import settings


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Создание JWT access токена.

    Args:
        data: Payload данные (обычно {"sub": user_id, "role": role})
        expires_delta: Время жизни токена (если None - берётся из настроек)

    Returns:
        Закодированный JWT токен
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access"
    })

    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


def create_refresh_token(data: Dict[str, Any]) -> str:
    """
    Создание JWT refresh токена для обновления access токена.

    Args:
        data: Payload данные

    Returns:
        Закодированный JWT refresh токен
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "refresh"
    })

    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Декодирование и валидация JWT токена.

    Args:
        token: JWT токен

    Returns:
        Payload данные или None если токен невалидный
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError:
        return None


def verify_token(token: str, token_type: str = "access") -> Optional[Dict[str, Any]]:
    """
    Проверка токена на валидность и тип.

    Args:
        token: JWT токен
        token_type: Ожидаемый тип токена (access или refresh)

    Returns:
        Payload данные или None если проверка не прошла
    """
    payload = decode_token(token)

    if not payload:
        return None

    if payload.get("type") != token_type:
        return None

    return payload
