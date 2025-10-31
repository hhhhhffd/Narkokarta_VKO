"""
Telegram бот для работы с Наркокартой.

Возможности:
- Авторизация через кнопку "Поделиться контактом"
- Создание меток через отправку геолокации
- Просмотр меток рядом
- Загрузка фото для меток

Установка:
pip install python-telegram-bot httpx

Запуск:
python telegram_bot.py
"""
import logging
import os

from telegram import (
    Update,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    WebAppInfo
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)
import httpx


# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# Конфигурация
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN")
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
WEBAPP_URL = os.getenv("WEBAPP_URL", "http://localhost:8000/web/index.html")


# HTTP клиент
http_client = httpx.AsyncClient(timeout=30.0)

# Дефолтные координаты (совпадают с центром карты)
DEFAULT_COORDINATES = {
    'lat': 49.948658972761386,
    'lon': 82.6267031181721
}


# ==================== Геокодинг ====================

async def geocode_address(address: str) -> dict:
    """
    Преобразование адреса в координаты через Nominatim API (OpenStreetMap)

    Args:
        address: Текстовый адрес

    Returns:
        dict с ключами 'lat', 'lon', 'success'
    """
    try:
        # Nominatim API - бесплатный геокодинг от OpenStreetMap
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            'q': address,
            'format': 'json',
            'limit': 1,
            'countrycodes': 'kz',  # Ограничиваем поиск Казахстаном
            'accept-language': 'ru'
        }
        headers = {
            'User-Agent': 'NarcoMap-Telegram-Bot/1.0'  # Nominatim требует User-Agent
        }

        response = await http_client.get(url, params=params, headers=headers, timeout=10.0)

        if response.status_code == 200:
            results = response.json()
            if results and len(results) > 0:
                location = results[0]
                return {
                    'lat': float(location['lat']),
                    'lon': float(location['lon']),
                    'success': True,
                    'display_name': location.get('display_name', address)
                }
    except Exception as e:
        logger.error(f"Ошибка геокодинга: {e}")

    # Если не получилось - возвращаем дефолтные координаты
    return {
        'lat': DEFAULT_COORDINATES['lat'],
        'lon': DEFAULT_COORDINATES['lon'],
        'success': False,
        'display_name': address
    }


# ==================== API Функции ====================

async def api_request_otp(phone: str) -> dict:
    """Запрос OTP кода"""
    try:
        response = await http_client.post(
            f"{API_BASE_URL}/auth/request-otp",
            json={"phone": phone}
        )
        return response.json()
    except Exception as e:
        logger.error(f"Ошибка запроса OTP: {e}")
        return {"success": False, "message": str(e)}


async def api_verify_otp(phone: str, code: str) -> dict:
    """Верификация OTP"""
    try:
        response = await http_client.post(
            f"{API_BASE_URL}/auth/verify-otp",
            json={"phone": phone, "code": code}
        )
        return response.json()
    except Exception as e:
        logger.error(f"Ошибка верификации OTP: {e}")
        return {}


async def api_create_marker(token: str, marker_data: dict) -> dict:
    """Создание метки"""
    try:
        response = await http_client.post(
            f"{API_BASE_URL}/markers",
            headers={"Authorization": f"Bearer {token}"},
            json=marker_data
        )
        return response.json()
    except Exception as e:
        logger.error(f"Ошибка создания метки: {e}")
        return {}


async def api_get_markers(filters: dict) -> list:
    """Получение меток"""
    try:
        response = await http_client.get(
            f"{API_BASE_URL}/markers",
            params=filters
        )
        return response.json()
    except Exception as e:
        logger.error(f"Ошибка получения меток: {e}")
        return []


async def api_upload_photo(token: str, marker_id: int, photo_path: str) -> dict:
    """Загрузка фото для метки"""
    try:
        with open(photo_path, 'rb') as f:
            files = {'photo': f}
            response = await http_client.post(
                f"{API_BASE_URL}/markers/{marker_id}/photo",
                headers={"Authorization": f"Bearer {token}"},
                files=files
            )
        return response.json()
    except Exception as e:
        logger.error(f"Ошибка загрузки фото: {e}")
        return {}


async def api_get_user_stats(token: str) -> dict:
    """Статистика пользователя"""
    try:
        response = await http_client.get(
            f"{API_BASE_URL}/users/me/stats",
            headers={"Authorization": f"Bearer {token}"}
        )
        return response.json()
    except Exception as e:
        logger.error(f"Ошибка получения статистики: {e}")
        return {}


# ==================== Клавиатуры ====================

def get_main_keyboard(is_authenticated: bool = False):
    """Главная клавиатура"""
    if not is_authenticated:
        keyboard = [
            [KeyboardButton("🗺 Открыть карту", web_app=WebAppInfo(url=WEBAPP_URL))],
            [KeyboardButton("🔑 Войти", request_contact=True)]
        ]
    else:
        keyboard = [
            [KeyboardButton("🗺 Открыть карту", web_app=WebAppInfo(url=WEBAPP_URL))],
            [KeyboardButton("📍 Создать метку")],  # Убрали request_location=True
            [KeyboardButton("🗺 Метки рядом")],
            [KeyboardButton("📊 Моя статистика")],
            [KeyboardButton("ℹ️ Помощь"), KeyboardButton("🚪 Выйти")]
        ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_marker_creation_method_keyboard():
    """Клавиатура выбора способа создания метки"""
    keyboard = [
        [
            InlineKeyboardButton("📍 Отправить геолокацию", callback_data="method_geo")
        ],
        [
            InlineKeyboardButton("✍️ Ввести данные вручную", callback_data="method_manual")
        ],
        [
            InlineKeyboardButton("❌ Отмена", callback_data="cancel")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_marker_type_keyboard():
    """Клавиатура выбора типа метки"""
    keyboard = [
        [
            InlineKeyboardButton("🏚 Притон", callback_data="type_den"),
            InlineKeyboardButton("📢 Реклама", callback_data="type_ad")
        ],
        [
            InlineKeyboardButton("🚶 Курьер", callback_data="type_courier"),
            InlineKeyboardButton("💊 Употребление", callback_data="type_user")
        ],
        [
            InlineKeyboardButton("🗑 Мусор", callback_data="type_trash")
        ],
        [
            InlineKeyboardButton("❌ Отмена", callback_data="cancel")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)




# ==================== Обработчики команд ====================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    user = update.effective_user
    is_auth = context.user_data.get('access_token') is not None

    welcome_text = f"""
👋 Привет, {user.first_name}!

Добро пожаловать в Наркокарту - сервис картографирования проблемных точек.

{'🔓 Вы авторизованы! Используйте кнопки ниже.' if is_auth else '🔒 Для начала работы авторизуйтесь, нажав кнопку "🔑 Войти"'}

🗺 **Открыть карту** - интерактивная карта со всеми метками
📍 Создавайте метки с геолокацией
🗺 Просматривайте метки рядом
📊 Отслеживайте статистику

Все метки сразу появляются на карте!
"""

    await update.message.reply_text(
        welcome_text,
        reply_markup=get_main_keyboard(is_auth),
        parse_mode='Markdown'
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /help"""
    help_text = """
ℹ️ *Помощь*

*Основные функции:*
🗺 Открыть карту - Интерактивная карта со всеми метками (WebApp)
📍 Создать метку - Отправьте геолокацию и опишите проблему
🗺 Метки рядом - Посмотрите метки в вашем районе
📊 Статистика - Ваши метки и активность

*Типы меток:*
🔴 Притон - Места употребления/продажи
🟠 Реклама - Объявления о наркотиках
🟡 Курьер - Распространитель и точки встречи
🟢 Употребление - Места употребления
⚪️ Мусор - Шприцы и другой мусор

*Работа с картой:*
• Нажмите кнопку "🗺 Открыть карту"
• Используйте фильтры для поиска нужных меток
• Кликайте на метки для просмотра деталей
• Создавайте новые метки прямо на карте

*Процесс создания метки:*
1. Нажмите "📍 Создать метку" или откройте карту
2. Отправьте геолокацию или кликните на карте
3. Выберите тип метки (цвет определится автоматически)
4. Опишите проблему
5. По желанию прикрепите фото
6. Метка сразу появится на карте!

*Команды:*
/start - Главное меню
/map - Открыть карту
/help - Эта справка

Вопросы? Пишите /support
"""

    await update.message.reply_text(
        help_text,
        parse_mode='Markdown'
    )


async def map_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /map - открыть карту"""
    keyboard = [
        [InlineKeyboardButton("🗺 Открыть карту", web_app=WebAppInfo(url=WEBAPP_URL))]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🗺 *Интерактивная карта*\n\n"
        "Нажмите кнопку ниже, чтобы открыть карту со всеми метками.\n\n"
        "На карте вы можете:\n"
        "• Просматривать все одобренные метки\n"
        "• Фильтровать по типу и опасности\n"
        "• Создавать новые метки кликом\n"
        "• Видеть фото и описания\n\n"
        "Карта поддерживает кластеризацию - близкие метки группируются автоматически.",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def logout_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выход из аккаунта"""
    context.user_data.clear()
    await update.message.reply_text(
        "👋 Вы вышли из аккаунта",
        reply_markup=get_main_keyboard(False)
    )


# ==================== Обработчики авторизации ====================

async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка контакта (номера телефона)"""
    contact = update.message.contact

    # Проверяем что это контакт самого пользователя
    if contact.user_id != update.effective_user.id:
        await update.message.reply_text(
            "❌ Пожалуйста, отправьте свой номер телефона"
        )
        return

    phone = f"+{contact.phone_number}"

    # Запрос OTP
    await update.message.reply_text("⏳ Отправляем код...")

    result = await api_request_otp(phone)

    if result.get("success"):
        # Сохраняем номер в контексте
        context.user_data['phone'] = phone
        context.user_data['awaiting'] = 'otp'

        # Показываем код в разработке
        code_text = f"\n\n🔢 Код (для разработки): `{result.get('code')}`" if result.get('code') else ""

        await update.message.reply_text(
            f"✅ {result['message']}{code_text}\n\n"
            f"Введите код подтверждения:",
            parse_mode='Markdown',
            reply_markup=ReplyKeyboardRemove()
        )
    else:
        await update.message.reply_text(
            f"❌ Ошибка: {result.get('message', 'Неизвестная ошибка')}\n\n"
            f"Попробуйте снова: /start",
            reply_markup=get_main_keyboard(False)
        )


async def handle_otp_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка OTP кода"""
    if context.user_data.get('awaiting') != 'otp':
        return

    phone = context.user_data.get('phone')
    code = update.message.text.strip()

    # Верификация OTP
    await update.message.reply_text("⏳ Проверяем код...")

    result = await api_verify_otp(phone, code)

    if result.get('access_token'):
        # Сохраняем токен
        context.user_data['access_token'] = result['access_token']
        context.user_data['refresh_token'] = result['refresh_token']
        context.user_data['user_id'] = result['user_id']
        context.user_data['role'] = result['role']
        context.user_data['awaiting'] = None

        await update.message.reply_text(
            f"✅ Авторизация успешна!\n\n"
            f"👤 ID: {result['user_id']}\n"
            f"🎭 Роль: {result['role']}\n\n"
            f"Используйте кнопки ниже для работы с картой.",
            reply_markup=get_main_keyboard(True)
        )
    else:
        await update.message.reply_text(
            "❌ Неверный код\n\n"
            "Попробуйте снова или нажмите /start для нового кода"
        )


# ==================== Создание меток ====================

async def handle_location_for_marker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка геолокации для создания метки или поиска рядом"""
    token = context.user_data.get('access_token')

    if not token:
        await update.message.reply_text(
            "🔒 Сначала авторизуйтесь: нажмите 🔑 Войти",
            reply_markup=get_main_keyboard(False)
        )
        return

    location = update.message.location
    lat = location.latitude
    lon = location.longitude

    # Проверяем режим работы из контекста
    awaiting = context.user_data.get('awaiting')
    mode = context.user_data.get('location_mode', 'create')

    if mode == 'nearby':
        # Ищем метки рядом
        context.user_data['location_mode'] = None  # Сбрасываем режим
        return await handle_location_for_nearby_internal(update, context, lat, lon)

    # Создание новой метки
    if awaiting == 'marker_location':
        context.user_data['marker_lat'] = lat
        context.user_data['marker_lon'] = lon

        # Автоматический адрес (координаты)
        auto_address = f"Координаты: {lat:.6f}, {lon:.6f}"
        context.user_data['marker_address'] = auto_address
        context.user_data['awaiting'] = 'marker_type'

        await update.message.reply_text(
            f"✅ Геолокация получена!\n\n"
            f"📍 Широта: {lat:.6f}\n"
            f"📍 Долгота: {lon:.6f}\n\n"
            f"Выберите тип метки:",
            reply_markup=get_marker_type_keyboard()
        )
    else:
        # Старая логика для обратной совместимости
        context.user_data['marker_lat'] = lat
        context.user_data['marker_lon'] = lon
        context.user_data['awaiting'] = 'marker_type'

        await update.message.reply_text(
            f"📍 Координаты получены:\n"
            f"Широта: {lat:.6f}\n"
            f"Долгота: {lon:.6f}\n\n"
            f"Выберите тип метки:",
            reply_markup=get_marker_type_keyboard()
        )


async def handle_cancel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Универсальная обработка отмены"""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("❌ Действие отменено")
    context.user_data['awaiting'] = None
    context.user_data['creation_method'] = None


async def handle_creation_method_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора способа создания метки"""
    query = update.callback_query
    await query.answer()

    if query.data == "cancel":
        return await handle_cancel_callback(update, context)

    if query.data == "method_geo":
        # Запрашиваем геолокацию
        context.user_data['creation_method'] = 'geo'
        context.user_data['awaiting'] = 'marker_location'

        await query.edit_message_text(
            "📍 *Отправьте геолокацию*\n\n"
            "Нажмите на скрепку 📎 и выберите 'Геопозиция'\n"
            "или используйте кнопку ниже.\n\n"
            "⚠️ *Важно:* Telegram может запросить разрешение на доступ к геолокации.\n"
            "Если у вас не получается отправить геолокацию, используйте ручной ввод.",
            parse_mode='Markdown'
        )

        # Отправляем клавиатуру с кнопкой геолокации и возможностью отмены
        keyboard = ReplyKeyboardMarkup(
            [
                [KeyboardButton("📍 Отправить геолокацию", request_location=True)],
                [KeyboardButton("✍️ Перейти к ручному вводу")]
            ],
            resize_keyboard=True,
            one_time_keyboard=True
        )
        await query.message.reply_text(
            "👇 Используйте кнопку для отправки геолокации\n"
            "или переключитесь на ручной ввод:",
            reply_markup=keyboard
        )

    elif query.data == "method_manual":
        # Ручной ввод адреса/координат
        context.user_data['creation_method'] = 'manual'
        context.user_data['awaiting'] = 'marker_coordinates'

        await query.edit_message_text(
            "✍️ *Ручной ввод адреса*\n\n"
            "Отправьте адрес текстом, например:\n"
            "`Астана, ул. Пушкина, д. 10, кв. 5`\n"
            "`ул. Абая 15, 3 этаж`\n\n"
            "💡 Координаты будут найдены автоматически!\n\n"
            "Также можете отправить координаты в формате:\n"
            "`51.1694, 71.4491`",
            parse_mode='Markdown'
        )


async def handle_marker_type_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора типа метки"""
    query = update.callback_query
    await query.answer()

    if query.data == "cancel":
        return await handle_cancel_callback(update, context)

    # Сохраняем тип
    marker_type = query.data.replace("type_", "")
    context.user_data['marker_type'] = marker_type

    # Автоматически определяем цвет по типу
    type_to_color = {
        "den": "red",
        "ad": "orange",
        "courier": "yellow",
        "user": "green",
        "trash": "white"
    }
    context.user_data['marker_color'] = type_to_color.get(marker_type, "yellow")
    context.user_data['awaiting'] = 'marker_description'

    type_names = {
        "den": "🏚 Притон",
        "ad": "📢 Реклама",
        "courier": "🚶 Курьер",
        "user": "💊 Употребление",
        "trash": "🗑 Мусор"
    }

    color_names = {
        "red": "🔴 Критично",
        "orange": "🟠 Высокая опасность",
        "yellow": "🟡 Средняя опасность",
        "green": "🟢 Низкая опасность",
        "white": "⚪️ Нейтрально"
    }

    marker_color = context.user_data['marker_color']
    lat = context.user_data.get('marker_lat')
    lon = context.user_data.get('marker_lon')
    address = context.user_data.get('marker_address', 'Не указан')

    await query.edit_message_text(
        f"✅ Тип: {type_names.get(marker_type, marker_type)}\n"
        f"✅ Опасность: {color_names.get(marker_color, marker_color)} (определено автоматически)\n\n"
        f"📍 Координаты: {lat:.6f}, {lon:.6f}\n"
        f"📫 Адрес: {address}\n\n"
        f"📝 Отправьте описание проблемы (опционально) или нажмите /skip чтобы пропустить."
    )


async def handle_manual_coordinates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ручного ввода координат или адреса"""
    if context.user_data.get('awaiting') != 'marker_coordinates':
        return

    text = update.message.text.strip()

    # Пробуем распарсить как координаты (формат: lat, lon)
    try:
        parts = text.replace(',', ' ').split()
        if len(parts) >= 2:
            lat = float(parts[0])
            lon = float(parts[1])

            # Проверяем валидность координат
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                context.user_data['marker_lat'] = lat
                context.user_data['marker_lon'] = lon
                context.user_data['marker_address'] = f"Координаты: {lat:.6f}, {lon:.6f}"
                context.user_data['awaiting'] = 'marker_type'

                await update.message.reply_text(
                    f"✅ Координаты приняты!\n\n"
                    f"📍 Широта: {lat:.6f}\n"
                    f"📍 Долгота: {lon:.6f}\n\n"
                    f"Выберите тип метки:",
                    reply_markup=get_marker_type_keyboard()
                )
                return
    except (ValueError, IndexError):
        pass

    # Если не распарсилось как координаты - это текстовый адрес
    # Пробуем найти координаты через геокодинг
    await update.message.reply_text(
        f"📫 Адрес принят: {text}\n\n"
        f"🔍 Ищу координаты для этого адреса...",
    )

    # Геокодинг адреса
    geocode_result = await geocode_address(text)

    # Сохраняем данные и переходим к выбору типа метки
    context.user_data['marker_lat'] = geocode_result['lat']
    context.user_data['marker_lon'] = geocode_result['lon']
    context.user_data['marker_address'] = text
    context.user_data['awaiting'] = 'marker_type'

    if geocode_result['success']:
        # Успешно нашли координаты
        await update.message.reply_text(
            f"✅ Координаты найдены автоматически!\n\n"
            f"📍 Широта: {geocode_result['lat']:.6f}\n"
            f"📍 Долгота: {geocode_result['lon']:.6f}\n"
            f"📫 Адрес: {text}\n"
            f"🗺 Полный адрес: {geocode_result['display_name']}\n\n"
            f"Выберите тип метки:",
            reply_markup=get_marker_type_keyboard()
        )
    else:
        # Не удалось найти координаты - используем дефолтные
        await update.message.reply_text(
            f"⚠️ Не удалось найти точные координаты для этого адреса.\n\n"
            f"Использованы дефолтные координаты:\n"
            f"📍 Широта: {geocode_result['lat']:.6f}\n"
            f"📍 Долгота: {geocode_result['lon']:.6f}\n"
            f"📫 Адрес: {text}\n\n"
            f"💡 *Совет:* Укажите более полный адрес для точного поиска.\n\n"
            f"Выберите тип метки:",
            parse_mode='Markdown',
            reply_markup=get_marker_type_keyboard()
        )




async def handle_marker_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка адреса метки"""
    if context.user_data.get('awaiting') != 'marker_address':
        return

    address = update.message.text
    context.user_data['marker_address'] = address
    context.user_data['awaiting'] = 'marker_description'

    await update.message.reply_text(
        f"✅ Адрес: {address}\n\n"
        f"📝 Теперь отправьте описание проблемы (опционально).\n"
        f"Или отправьте /skip чтобы пропустить."
    )


async def handle_marker_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка описания метки"""
    if context.user_data.get('awaiting') != 'marker_description':
        return

    description = update.message.text if update.message.text != '/skip' else None
    token = context.user_data.get('access_token')

    # Создаём метку
    await update.message.reply_text("⏳ Создаём метку...")

    marker_data = {
        "title": f"Метка от {update.effective_user.first_name}",
        "address": context.user_data.get('marker_address'),
        "description": description,
        "latitude": context.user_data['marker_lat'],
        "longitude": context.user_data['marker_lon'],
        "type": context.user_data['marker_type'],
        "color": context.user_data['marker_color']
    }

    result = await api_create_marker(token, marker_data)

    if result.get('id'):
        context.user_data['last_marker_id'] = result['id']
        context.user_data['awaiting'] = 'marker_photo_optional'

        type_emoji = {"den": "🏚", "ad": "📢", "courier": "🚶", "user": "💊", "trash": "🗑"}
        color_emoji = {"red": "🔴", "orange": "🟠", "yellow": "🟡", "green": "🟢", "white": "⚪️"}

        await update.message.reply_text(
            f"✅ Метка создана и сразу появилась на карте!\n\n"
            f"🆔 ID: {result['id']}\n"
            f"{type_emoji.get(result['type'], '📍')} Тип: {result['type']}\n"
            f"{color_emoji.get(result['color'], '⚪️')} Опасность: {result['color']}\n"
            f"📊 Статус: опубликована\n\n"
            f"📸 Хотите добавить фото? Отправьте фото или нажмите /skip",
            reply_markup=get_main_keyboard(True)
        )
    else:
        await update.message.reply_text(
            "❌ Ошибка создания метки\n\n"
            "Возможные причины:\n"
            "• Превышен дневной лимит\n"
            "• Слишком близко к другой метке\n"
            "• Проблемы с подключением\n\n"
            "Попробуйте позже",
            reply_markup=get_main_keyboard(True)
        )

    context.user_data['awaiting'] = None


async def handle_marker_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка фото для метки"""
    if not context.user_data.get('last_marker_id'):
        return

    token = context.user_data.get('access_token')
    marker_id = context.user_data['last_marker_id']

    # Получаем фото
    photo = update.message.photo[-1]  # Самое большое разрешение
    file = await photo.get_file()

    # Скачиваем фото
    photo_path = f"/tmp/marker_{marker_id}_{photo.file_id}.jpg"
    await file.download_to_drive(photo_path)

    await update.message.reply_text("⏳ Загружаем фото...")

    # Загружаем на сервер
    result = await api_upload_photo(token, marker_id, photo_path)

    # Удаляем временный файл
    os.remove(photo_path)

    if result.get('id'):
        await update.message.reply_text(
            "✅ Фото добавлено к метке!\n\n"
            "Метка уже видна на карте.",
            reply_markup=get_main_keyboard(True)
        )
    else:
        await update.message.reply_text(
            "❌ Ошибка загрузки фото\n\n"
            "Метка создана без фото, но уже видна на карте.",
            reply_markup=get_main_keyboard(True)
        )

    context.user_data['last_marker_id'] = None


async def skip_photo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Пропустить добавление фото"""
    await update.message.reply_text(
        "✅ Метка опубликована на карте без фото",
        reply_markup=get_main_keyboard(True)
    )
    context.user_data['last_marker_id'] = None


# ==================== Просмотр меток ====================

async def handle_location_for_nearby_internal(update: Update, context: ContextTypes.DEFAULT_TYPE, lat: float, lon: float):
    """Внутренняя функция для поиска меток рядом"""
    await update.message.reply_text("🔍 Ищем метки рядом...")

    # Получаем метки
    markers = await api_get_markers({
        "center_lat": lat,
        "center_lon": lon,
        "radius_km": 5
    })

    if not markers:
        await update.message.reply_text(
            "📭 Меток рядом не найдено (радиус 5 км)",
            reply_markup=get_main_keyboard(True)
        )
        return

    # Формируем сообщение
    type_emoji = {"den": "🏚", "ad": "📢", "courier": "🚶", "user": "💊", "trash": "🗑"}
    color_emoji = {"red": "🔴", "orange": "🟠", "yellow": "🟡", "green": "🟢", "white": "⚪️"}

    message = f"🗺 Найдено меток: {len(markers)}\n\n"

    for i, marker in enumerate(markers[:10], 1):  # Показываем первые 10
        message += (
            f"{i}. {type_emoji.get(marker['type'], '📍')} *{marker['title']}*\n"
            f"   {color_emoji.get(marker['color'], '⚪️')} {marker['type']} • {marker['color']}\n"
            f"   📍 [{marker['latitude']:.5f}, {marker['longitude']:.5f}](https://www.google.com/maps?q={marker['latitude']},{marker['longitude']})\n"
        )

        if marker.get('description'):
            desc = marker['description'][:50] + "..." if len(marker['description']) > 50 else marker['description']
            message += f"   💬 {desc}\n"

        message += "\n"

    if len(markers) > 10:
        message += f"_...и ещё {len(markers) - 10} меток_\n"

    await update.message.reply_text(
        message,
        parse_mode='Markdown',
        disable_web_page_preview=True,
        reply_markup=get_main_keyboard(True)
    )


# ==================== Статистика ====================

async def handle_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Статистика пользователя"""
    token = context.user_data.get('access_token')

    if not token:
        await update.message.reply_text(
            "🔒 Сначала авторизуйтесь",
            reply_markup=get_main_keyboard(False)
        )
        return

    await update.message.reply_text("⏳ Загружаем статистику...")

    stats = await api_get_user_stats(token)

    if stats:
        await update.message.reply_text(
            f"📊 *Ваша статистика*\n\n"
            f"👤 ID: `{stats['user_id']}`\n"
            f"📱 Телефон: `{stats['phone']}`\n"
            f"🎭 Роль: {stats['role']}\n\n"
            f"📍 Всего меток: *{stats['total_markers']}*\n"
            f"📅 Активность сегодня: {stats['today_activities']}\n"
            f"⏳ Осталось сегодня: {stats['daily_limit_remaining']}\n",
            parse_mode='Markdown',
            reply_markup=get_main_keyboard(True)
        )
    else:
        await update.message.reply_text(
            "❌ Ошибка получения статистики",
            reply_markup=get_main_keyboard(True)
        )


# ==================== Обработчик сообщений ====================

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстовых сообщений"""
    text = update.message.text

    # Проверяем состояние ожидания
    awaiting = context.user_data.get('awaiting')

    if awaiting == 'otp':
        return await handle_otp_code(update, context)
    elif awaiting == 'marker_coordinates':
        return await handle_manual_coordinates(update, context)
    elif awaiting == 'marker_address':
        return await handle_marker_address(update, context)
    elif awaiting == 'marker_description':
        return await handle_marker_description(update, context)

    # Обработка кнопок
    if "перейти к ручному вводу" in text.lower():
        # Переключаемся на ручной ввод из режима геолокации
        context.user_data['creation_method'] = 'manual'
        context.user_data['awaiting'] = 'marker_coordinates'

        await update.message.reply_text(
            "✍️ *Ручной ввод адреса*\n\n"
            "Отправьте адрес текстом, например:\n"
            "`Астана, ул. Пушкина, д. 10, кв. 5`\n"
            "`ул. Абая 15, 3 этаж`\n\n"
            "💡 Координаты будут найдены автоматически!\n\n"
            "Также можете отправить координаты в формате:\n"
            "`51.1694, 71.4491`",
            parse_mode='Markdown',
            reply_markup=get_main_keyboard(True)
        )
        return

    if "рядом" in text.lower():
        # Устанавливаем режим "поиск рядом" и просим геолокацию
        context.user_data['location_mode'] = 'nearby'
        await update.message.reply_text(
            "📍 Отправьте вашу геолокацию, чтобы найти метки рядом",
            reply_markup=ReplyKeyboardMarkup(
                [[KeyboardButton("📍 Отправить локацию", request_location=True)]],
                resize_keyboard=True,
                one_time_keyboard=True
            )
        )
    elif "создать метку" in text.lower():
        # Проверяем авторизацию
        token = context.user_data.get('access_token')
        if not token:
            await update.message.reply_text(
                "🔒 Сначала авторизуйтесь: нажмите 🔑 Войти",
                reply_markup=get_main_keyboard(False)
            )
            return

        # Показываем выбор способа создания метки
        await update.message.reply_text(
            "📍 *Создание метки*\n\n"
            "Выберите способ создания метки:",
            reply_markup=get_marker_creation_method_keyboard(),
            parse_mode='Markdown'
        )
    elif "статистика" in text.lower():
        return await handle_stats(update, context)
    elif "помощь" in text.lower():
        return await help_command(update, context)
    elif "выйти" in text.lower():
        return await logout_command(update, context)
    else:
        await update.message.reply_text(
            "❓ Используйте кнопки меню или /help для справки"
        )


# ==================== Главная функция ====================

def main():
    """Запуск бота"""
    if TELEGRAM_BOT_TOKEN == "YOUR_BOT_TOKEN":
        print("❌ Ошибка: Установите TELEGRAM_BOT_TOKEN")
        print("Получите токен у @BotFather и установите переменную окружения:")
        print("export TELEGRAM_BOT_TOKEN='your-token-here'")
        return

    print(f"🤖 Запуск Telegram бота...")
    print(f"📡 API: {API_BASE_URL}")

    # Создание приложения
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Команды
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("map", map_command))
    application.add_handler(CommandHandler("logout", logout_command))
    application.add_handler(CommandHandler("skip", skip_photo_command))

    # Контакт (авторизация)
    application.add_handler(MessageHandler(filters.CONTACT, handle_contact))

    # Геолокация
    application.add_handler(MessageHandler(filters.LOCATION, handle_location_for_marker))

    # Фото
    application.add_handler(MessageHandler(filters.PHOTO, handle_marker_photo))

    # Callback queries (inline кнопки)
    # Выбор способа создания метки
    application.add_handler(CallbackQueryHandler(
        handle_creation_method_callback,
        pattern="^method_"
    ))

    # Выбор типа метки
    application.add_handler(CallbackQueryHandler(
        handle_marker_type_callback,
        pattern="^type_"
    ))

    # Отмена - обрабатываем для всех типов callback
    application.add_handler(CallbackQueryHandler(
        handle_cancel_callback,
        pattern="^cancel$"
    ))

    # Текстовые сообщения
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_text
    ))

    # Запуск
    print("✅ Бот запущен!")
    print("Остановка: Ctrl+C")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
