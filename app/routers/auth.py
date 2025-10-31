"""
Роутер авторизации: OTP + JWT flow.

Процесс авторизации:
1. POST /auth/request-otp - запрос OTP кода на телефон
2. POST /auth/verify-otp - проверка OTP и получение JWT токенов
3. POST /auth/refresh - обновление access токена через refresh токен
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
import phonenumbers

from ..database import get_db
from ..auth.otp import create_otp, verify_otp, get_or_create_user
from ..auth.jwt import create_access_token, create_refresh_token, verify_token


router = APIRouter(prefix="/auth", tags=["Authentication"])


# Pydantic модели для запросов/ответов
class RequestOTPRequest(BaseModel):
    phone: str = Field(..., description="Номер телефона в международном формате (+79991234567)")


class RequestOTPResponse(BaseModel):
    success: bool
    message: str
    # В разработке можем возвращать код для удобства тестирования
    code: str | None = None


class VerifyOTPRequest(BaseModel):
    phone: str = Field(..., description="Номер телефона")
    code: str = Field(..., description="OTP код из SMS")


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: int
    role: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


@router.post("/request-otp", response_model=RequestOTPResponse)
def request_otp(request: RequestOTPRequest, db: Session = Depends(get_db)):
    """
    Запрос OTP кода на телефон.

    Процесс:
    1. Валидация номера телефона
    2. Генерация OTP кода
    3. Логирование кода в файл (для разработки)
    4. Отправка SMS
    5. Возврат успеха

    Пример запроса:
    ```
    POST /auth/request-otp
    {
        "phone": "+79991234567"
    }
    ```

    Пример ответа:
    ```
    {
        "success": true,
        "message": "OTP код отправлен на +79991234567",
        "code": "123456"  // только в DEBUG режиме
    }
    ```
    """
    # Валидация номера телефона
    try:
        parsed = phonenumbers.parse(request.phone, None)
        if not phonenumbers.is_valid_number(parsed):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Невалидный номер телефона"
            )
        phone = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Невалидный формат номера телефона. Используйте международный формат (+79991234567)"
        )

    # Создание и отправка OTP
    try:
        code = create_otp(db, phone)
        return RequestOTPResponse(
            success=True,
            message=f"OTP код отправлен на {phone}",
            code=code if db.bind.url.database == "narcomap.db" else None  # Возвращаем только для SQLite (разработка)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка отправки OTP: {str(e)}"
        )


@router.post("/verify-otp", response_model=TokenResponse)
def verify_otp_endpoint(request: VerifyOTPRequest, db: Session = Depends(get_db)):
    """
    Верификация OTP кода и получение JWT токенов.

    Процесс:
    1. Проверка OTP кода
    2. Получение или создание пользователя
    3. Генерация access и refresh токенов
    4. Возврат токенов

    Пример запроса:
    ```
    POST /auth/verify-otp
    {
        "phone": "+79991234567",
        "code": "123456"
    }
    ```

    Пример ответа:
    ```
    {
        "access_token": "eyJhbGciOiJIUzI1NiIs...",
        "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
        "token_type": "bearer",
        "user_id": 1,
        "role": "user"
    }
    ```

    Далее используйте access_token в заголовке:
    ```
    Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
    ```
    """
    # Нормализация номера
    try:
        parsed = phonenumbers.parse(request.phone, None)
        phone = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Невалидный формат номера телефона"
        )

    # Проверка OTP
    if not verify_otp(db, phone, request.code):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный или истекший OTP код"
        )

    # Получение/создание пользователя
    user = get_or_create_user(db, phone)

    # Генерация токенов
    token_data = {"sub": str(user.id), "role": user.role.value}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user_id=user.id,
        role=user.role.value
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh_token_endpoint(request: RefreshTokenRequest, db: Session = Depends(get_db)):
    """
    Обновление access токена через refresh токен.

    Процесс:
    1. Валидация refresh токена
    2. Извлечение user_id из токена
    3. Генерация нового access токена
    4. Возврат нового access токена (refresh остаётся прежним)

    Пример запроса:
    ```
    POST /auth/refresh
    {
        "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
    }
    ```

    Пример ответа:
    ```
    {
        "access_token": "eyJhbGciOiJIUzI1NiIs...",  // новый
        "refresh_token": "eyJhbGciOiJIUzI1NiIs...",  // тот же
        "token_type": "bearer",
        "user_id": 1,
        "role": "user"
    }
    ```
    """
    # Валидация refresh токена
    payload = verify_token(request.refresh_token, token_type="refresh")
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Невалидный refresh токен"
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Невалидный формат токена"
        )

    # Проверка существования пользователя
    from ..models import User
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь не найден"
        )

    # Генерация нового access токена
    token_data = {"sub": str(user.id), "role": user.role.value}
    new_access_token = create_access_token(token_data)

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=request.refresh_token,  # Возвращаем тот же refresh
        user_id=user.id,
        role=user.role.value
    )
