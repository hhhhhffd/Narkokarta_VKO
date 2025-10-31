"""
Telegram Bot адаптер для интеграции с Telegram.

Позволяет пользователям взаимодействовать с API через Telegram бота.

Основные функции:
- Авторизация по номеру телефона через OTP
- Создание меток с координатами и фото
- Просмотр меток на карте
- Получение уведомлений о модерации

Установка:
pip install python-telegram-bot

Настройка:
1. Создайте бота через @BotFather
2. Получите токен
3. Установите переменную TELEGRAM_BOT_TOKEN
4. Запустите бота: python telegram_bot.py
"""
import httpx
import logging
from typing import Optional, Dict, Any

from ..config import settings


logger = logging.getLogger(__name__)


class TelegramAdapter:
    """
    Адаптер для взаимодействия с Telegram Bot API.

    Пример использования в python-telegram-bot:

    ```python
    from telegram import Update
    from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes

    # Создаём адаптер для вызовов API
    adapter = TelegramAdapter(api_base_url="http://localhost:8000")

    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "Добро пожаловать в Наркокарту!\\n"
            "Отправьте /login для авторизации"
        )

    async def login(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "Отправьте ваш номер телефона в формате +79991234567"
        )
        context.user_data['awaiting'] = 'phone'

    async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if context.user_data.get('awaiting') == 'phone':
            phone = update.message.text
            # Запрос OTP
            result = await adapter.request_otp(phone)
            if result['success']:
                await update.message.reply_text(
                    f"Код отправлен на {phone}. Введите код:"
                )
                context.user_data['phone'] = phone
                context.user_data['awaiting'] = 'otp'

        elif context.user_data.get('awaiting') == 'otp':
            code = update.message.text
            phone = context.user_data['phone']
            # Верификация OTP
            result = await adapter.verify_otp(phone, code)
            if result['access_token']:
                context.user_data['access_token'] = result['access_token']
                await update.message.reply_text(
                    "Авторизация успешна!\\n"
                    "Отправьте геолокацию для создания метки"
                )
                context.user_data['awaiting'] = None

    async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
        token = context.user_data.get('access_token')
        if not token:
            await update.message.reply_text("Сначала авторизуйтесь: /login")
            return

        lat = update.message.location.latitude
        lon = update.message.location.longitude

        # Создание метки
        result = await adapter.create_marker(
            token=token,
            title="Метка из Telegram",
            latitude=lat,
            longitude=lon,
            marker_type="user"
        )

        if result:
            await update.message.reply_text(
                f"Метка создана! ID: {result['id']}\\n"
                f"Статус: {result['status']}"
            )

    # Запуск бота
    application = Application.builder().token("YOUR_BOT_TOKEN").build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("login", login))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.LOCATION, handle_location))
    application.run_polling()
    ```
    """

    def __init__(self, api_base_url: str = "http://localhost:8000"):
        self.api_base_url = api_base_url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=30.0)

    async def request_otp(self, phone: str) -> Dict[str, Any]:
        """
        Запрос OTP кода.

        Args:
            phone: Номер телефона

        Returns:
            {"success": bool, "message": str, "code": str|None}
        """
        try:
            response = await self.client.post(
                f"{self.api_base_url}/auth/request-otp",
                json={"phone": phone}
            )
            return response.json()
        except Exception as e:
            logger.error(f"Ошибка запроса OTP: {str(e)}")
            return {"success": False, "message": str(e)}

    async def verify_otp(self, phone: str, code: str) -> Dict[str, Any]:
        """
        Верификация OTP и получение токена.

        Args:
            phone: Номер телефона
            code: OTP код

        Returns:
            {"access_token": str, "refresh_token": str, "user_id": int, "role": str}
        """
        try:
            response = await self.client.post(
                f"{self.api_base_url}/auth/verify-otp",
                json={"phone": phone, "code": code}
            )
            return response.json()
        except Exception as e:
            logger.error(f"Ошибка верификации OTP: {str(e)}")
            return {}

    async def create_marker(
        self,
        token: str,
        title: str,
        latitude: float,
        longitude: float,
        marker_type: str,
        description: Optional[str] = None,
        color: str = "yellow"
    ) -> Optional[Dict[str, Any]]:
        """
        Создание метки.

        Args:
            token: Access токен
            title: Название
            latitude: Широта
            longitude: Долгота
            marker_type: Тип (den, ad, courier, user, trash)
            description: Описание
            color: Цвет (red, orange, yellow, green, white)

        Returns:
            Данные созданной метки или None
        """
        try:
            headers = {"Authorization": f"Bearer {token}"}
            payload = {
                "title": title,
                "description": description,
                "latitude": latitude,
                "longitude": longitude,
                "type": marker_type,
                "color": color
            }

            response = await self.client.post(
                f"{self.api_base_url}/markers",
                headers=headers,
                json=payload
            )

            if response.status_code == 201:
                return response.json()
            else:
                logger.error(f"Ошибка создания метки: {response.status_code} {response.text}")
                return None

        except Exception as e:
            logger.error(f"Ошибка создания метки: {str(e)}")
            return None

    async def get_nearby_markers(
        self,
        latitude: float,
        longitude: float,
        radius_km: float = 5.0
    ) -> list:
        """
        Получение меток в радиусе.

        Args:
            latitude: Широта центра
            longitude: Долгота центра
            radius_km: Радиус в км

        Returns:
            Список меток
        """
        try:
            params = {
                "center_lat": latitude,
                "center_lon": longitude,
                "radius_km": radius_km,
                "status": "approved"
            }

            response = await self.client.get(
                f"{self.api_base_url}/markers",
                params=params
            )

            if response.status_code == 200:
                return response.json()
            else:
                return []

        except Exception as e:
            logger.error(f"Ошибка получения меток: {str(e)}")
            return []

    async def close(self):
        """Закрытие HTTP клиента"""
        await self.client.aclose()
