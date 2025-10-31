"""
OTP (One-Time Password) генерация и верификация.
Коды отправляются через SMS адаптер и логируются для разработки/тестирования.

ВАЖНО: В продакшене обязательно отключить логирование OTP кодов в файл!
"""
import random
import string
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from typing import Optional
import logging
import os

from ..models import OTPCode, User
from ..config import settings
from ..adapters.sms_adapter import send_sms


# Настройка логгера для OTP
os.makedirs("logs", exist_ok=True)
otp_logger = logging.getLogger("otp")
otp_logger.setLevel(logging.INFO)

# Handler для записи в файл
file_handler = logging.FileHandler(settings.OTP_LOG_FILE)
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(message)s')
file_handler.setFormatter(formatter)
otp_logger.addHandler(file_handler)

# Handler для консоли (в debug режиме)
if settings.DEBUG:
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    otp_logger.addHandler(console_handler)


def generate_otp_code() -> str:
    """
    Генерация случайного OTP кода.

    Returns:
        Строка из цифр длиной OTP_LENGTH
    """
    return ''.join(random.choices(string.digits, k=settings.OTP_LENGTH))


def create_otp(db: Session, phone: str) -> str:
    """
    Создание и отправка OTP кода на телефон.

    Args:
        db: Сессия БД
        phone: Номер телефона

    Returns:
        Сгенерированный OTP код (для тестов, в продакшене не возвращаем!)

    Процесс:
    1. Деактивируем старые неиспользованные коды
    2. Генерируем новый код
    3. Сохраняем в БД
    4. ЛОГИРУЕМ код (только для разработки!)
    5. Отправляем через SMS адаптер
    """
    # Деактивируем старые коды
    old_codes = db.query(OTPCode).filter(
        OTPCode.phone == phone,
        OTPCode.is_used == False
    ).all()

    for old_code in old_codes:
        old_code.is_used = True
    db.commit()

    # Генерируем новый код
    code = generate_otp_code()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.OTP_EXPIRE_MINUTES)

    # Сохраняем в БД
    otp_record = OTPCode(
        phone=phone,
        code=code,
        expires_at=expires_at
    )
    db.add(otp_record)
    db.commit()

    # ЛОГИРУЕМ КОД - КРИТИЧЕСКИ ВАЖНО ДЛЯ РАЗРАБОТКИ
    # Формат: phone - code
    otp_logger.info(f"OTP for {phone}: {code}")

    # Отправляем SMS
    message = f"Ваш код подтверждения для Наркокарта: {code}. Действителен {settings.OTP_EXPIRE_MINUTES} мин."
    send_sms(phone, message)

    # В разработке возвращаем код для тестов
    # В продакшене этот return можно убрать
    return code


def verify_otp(db: Session, phone: str, code: str) -> bool:
    """
    Проверка OTP кода.

    Args:
        db: Сессия БД
        phone: Номер телефона
        code: OTP код для проверки

    Returns:
        True если код валиден, False если нет

    Проверки:
    - Код существует
    - Не использован ранее
    - Не истёк срок действия
    - Совпадает с введённым
    """
    otp_record = db.query(OTPCode).filter(
        OTPCode.phone == phone,
        OTPCode.code == code,
        OTPCode.is_used == False
    ).first()

    if not otp_record:
        return False

    # Проверка времени истечения
    expires_at = otp_record.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if datetime.now(timezone.utc) > expires_at:
        return False
    
    # Отмечаем код как использованный

    otp_record.is_used = True
    db.commit()
    return True



def get_or_create_user(db: Session, phone: str) -> User:
    """
    Получение существующего или создание нового пользователя.
    Вызывается после успешной OTP верификации.

    Args:
        db: Сессия БД
        phone: Номер телефона

    Returns:
        User объект
    """
    user = db.query(User).filter(User.phone == phone).first()

    if not user:
        # Создаём нового пользователя с ролью user по умолчанию
        user = User(
            phone=phone,
            role="user",
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    return user
