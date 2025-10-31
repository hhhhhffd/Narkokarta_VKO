"""
SMS адаптер для отправки OTP кодов.

Поддерживает:
- Mock режим (для разработки/тестирования)
- Twilio
- SMS.ru
- Любой кастомный HTTP-провайдер

Как добавить своего провайдера:
1. Добавьте функцию send_sms_<provider>(phone, message)
2. Добавьте проверку в send_sms()
3. Настройте переменные окружения
"""
import httpx
import logging
from typing import Optional

from ..config import settings


logger = logging.getLogger(__name__)


def send_sms(phone: str, message: str) -> bool:
    """
    Отправка SMS сообщения.

    Args:
        phone: Номер телефона в международном формате
        message: Текст сообщения

    Returns:
        True если успешно, False если ошибка

    Автоматически выбирает провайдера из настроек SMS_PROVIDER.
    """
    provider = settings.SMS_PROVIDER.lower()

    try:
        if provider == "mock":
            return send_sms_mock(phone, message)
        elif provider == "twilio":
            return send_sms_twilio(phone, message)
        elif provider == "smsru":
            return send_sms_smsru(phone, message)
        elif provider == "custom":
            return send_sms_custom(phone, message)
        else:
            logger.error(f"Неизвестный SMS провайдер: {provider}")
            return False
    except Exception as e:
        logger.error(f"Ошибка отправки SMS: {str(e)}")
        return False


def send_sms_mock(phone: str, message: str) -> bool:
    """
    Mock режим - логирует вместо отправки.

    Используется для разработки и тестирования.
    SMS не отправляется реально, только логируется.
    """
    logger.info(f"[MOCK SMS] To: {phone}, Message: {message}")
    print(f"[MOCK SMS] To: {phone}, Message: {message}")
    return True


def send_sms_twilio(phone: str, message: str) -> bool:
    """
    Отправка через Twilio.

    Требует:
    - pip install twilio
    - SMS_API_KEY = "account_sid:auth_token"

    Пример настроек:
    SMS_PROVIDER=twilio
    SMS_API_KEY=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxx:your_auth_token
    """
    try:
        from twilio.rest import Client

        # Парсим credentials из SMS_API_KEY
        account_sid, auth_token = settings.SMS_API_KEY.split(":")
        from_number = "+1234567890"  # TODO: вынести в настройки

        client = Client(account_sid, auth_token)
        message = client.messages.create(
            body=message,
            from_=from_number,
            to=phone
        )

        logger.info(f"SMS отправлен через Twilio: {message.sid}")
        return True

    except ImportError:
        logger.error("Twilio не установлен: pip install twilio")
        return False
    except Exception as e:
        logger.error(f"Ошибка отправки через Twilio: {str(e)}")
        return False


def send_sms_smsru(phone: str, message: str) -> bool:
    """
    Отправка через SMS.ru API.

    Требует:
    SMS_PROVIDER=smsru
    SMS_API_KEY=your-api-key

    API документация: https://sms.ru/api
    """
    try:
        url = "https://sms.ru/sms/send"
        params = {
            "api_id": settings.SMS_API_KEY,
            "to": phone,
            "msg": message,
            "json": 1
        }

        with httpx.Client() as client:
            response = client.get(url, params=params)
            data = response.json()

            if data.get("status") == "OK":
                logger.info(f"SMS отправлен через SMS.ru")
                return True
            else:
                logger.error(f"Ошибка SMS.ru: {data}")
                return False

    except Exception as e:
        logger.error(f"Ошибка отправки через SMS.ru: {str(e)}")
        return False


def send_sms_custom(phone: str, message: str) -> bool:
    """
    Отправка через кастомный HTTP-провайдер.

    Требует:
    SMS_PROVIDER=custom
    SMS_API_KEY=your-api-key
    SMS_API_URL=https://api.your-provider.com/send

    Формат запроса (настройте под своего провайдера):
    POST SMS_API_URL
    Headers:
        Authorization: Bearer SMS_API_KEY
    JSON:
        {
            "phone": "+79991234567",
            "message": "текст"
        }
    """
    try:
        headers = {
            "Authorization": f"Bearer {settings.SMS_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "phone": phone,
            "message": message
        }

        with httpx.Client() as client:
            response = client.post(
                settings.SMS_API_URL,
                headers=headers,
                json=payload,
                timeout=10.0
            )

            if response.status_code == 200:
                logger.info(f"SMS отправлен через кастомный провайдер")
                return True
            else:
                logger.error(f"Ошибка кастомного провайдера: {response.status_code} {response.text}")
                return False

    except Exception as e:
        logger.error(f"Ошибка отправки через кастомный провайдер: {str(e)}")
        return False


# Пример интеграции для других провайдеров
def send_sms_sinch(phone: str, message: str) -> bool:
    """
    Пример интеграции Sinch.

    TODO: Реализовать при необходимости
    """
    raise NotImplementedError("Sinch integration not implemented")


def send_sms_vonage(phone: str, message: str) -> bool:
    """
    Пример интеграции Vonage (Nexmo).

    TODO: Реализовать при необходимости
    """
    raise NotImplementedError("Vonage integration not implemented")
