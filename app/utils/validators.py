"""
Валидаторы для входных данных.
"""
import re
from typing import Tuple
import phonenumbers
from PIL import Image
import io


def validate_phone_number(phone: str) -> Tuple[bool, str]:
    """
    Валидация номера телефона.

    Args:
        phone: Номер телефона

    Returns:
        (валиден ли, нормализованный номер или сообщение об ошибке)
    """
    try:
        parsed = phonenumbers.parse(phone, None)
        if not phonenumbers.is_valid_number(parsed):
            return False, "Невалидный номер телефона"

        normalized = phonenumbers.format_number(
            parsed,
            phonenumbers.PhoneNumberFormat.E164
        )
        return True, normalized

    except phonenumbers.NumberParseException:
        return False, "Невалидный формат номера телефона. Используйте международный формат (+79991234567)"


def validate_coordinates(latitude: float, longitude: float) -> Tuple[bool, str]:
    """
    Валидация географических координат.

    Args:
        latitude: Широта
        longitude: Долгота

    Returns:
        (валидны ли, сообщение об ошибке)
    """
    if not (-90 <= latitude <= 90):
        return False, "Широта должна быть в диапазоне [-90, 90]"

    if not (-180 <= longitude <= 180):
        return False, "Долгота должна быть в диапазоне [-180, 180]"

    return True, ""


def validate_image(file_bytes: bytes, max_size_mb: int = 10) -> Tuple[bool, str]:
    """
    Валидация изображения.

    Args:
        file_bytes: Байты файла
        max_size_mb: Макс. размер в МБ

    Returns:
        (валидно ли, сообщение об ошибке)
    """
    # Проверка размера
    size_mb = len(file_bytes) / (1024 * 1024)
    if size_mb > max_size_mb:
        return False, f"Файл слишком большой. Макс. размер: {max_size_mb}MB"

    # Проверка что это действительно изображение
    try:
        img = Image.open(io.BytesIO(file_bytes))
        img.verify()

        # Проверка формата
        if img.format.lower() not in ['jpeg', 'jpg', 'png', 'gif']:
            return False, "Недопустимый формат изображения. Разрешены: JPEG, PNG, GIF"

        return True, ""

    except Exception:
        return False, "Файл не является валидным изображением"


def sanitize_text(text: str, max_length: int = 1000) -> str:
    """
    Очистка текста от опасных символов.

    Args:
        text: Входной текст
        max_length: Макс. длина

    Returns:
        Очищенный текст
    """
    if not text:
        return ""

    # Удаление HTML тегов
    text = re.sub(r'<[^>]*>', '', text)

    # Удаление лишних пробелов
    text = ' '.join(text.split())

    # Ограничение длины
    if len(text) > max_length:
        text = text[:max_length]

    return text.strip()


def validate_marker_title(title: str) -> Tuple[bool, str]:
    """
    Валидация названия метки.

    Args:
        title: Название

    Returns:
        (валидно ли, сообщение об ошибке)
    """
    if not title or len(title.strip()) < 3:
        return False, "Название должно содержать минимум 3 символа"

    if len(title) > 255:
        return False, "Название слишком длинное (макс. 255 символов)"

    # Проверка на спам (много повторяющихся символов)
    if len(set(title)) < 3:
        return False, "Название выглядит как спам"

    return True, ""
