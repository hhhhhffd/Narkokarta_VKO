# Telegram Бот - Инструкция

Telegram бот для работы с Наркокартой через мессенджер.

## Возможности

- 🔐 **Авторизация** через кнопку "Поделиться контактом"
- 📍 **Создание меток** через отправку геолокации
- 🗺 **Просмотр меток** рядом с вами
- 📸 **Загрузка фото** для меток
- 📊 **Статистика** пользователя
- 🎯 **Удобные кнопки** и inline-меню

## Установка

### 1. Установите зависимости

```bash
pip install python-telegram-bot httpx
```

Или установите из requirements.txt (если не установлено):

```bash
pip install -r requirements.txt
```

### 2. Создайте бота в Telegram

1. Найдите [@BotFather](https://t.me/BotFather) в Telegram
2. Отправьте команду `/newbot`
3. Придумайте имя бота (например: `Наркокарта`)
4. Придумайте username (например: `narcomap_bot`)
5. Скопируйте токен, который вам выдаст BotFather

### 3. Настройте переменные окружения

```bash
# Linux/Mac
export TELEGRAM_BOT_TOKEN="8338061887:AAFXVbnwOlvBqobrvngKsw_qf6ML7IY5DbY"
export API_BASE_URL="http://localhost:8000"

# Windows (CMD)
set TELEGRAM_BOT_TOKEN=your-bot-token-here
set API_BASE_URL=http://localhost:8000

# Windows (PowerShell)
$env:TELEGRAM_BOT_TOKEN="your-bot-token-here"
$env:API_BASE_URL="http://localhost:8000"
```

Или создайте файл `.env`:

```bash
TELEGRAM_BOT_TOKEN=your-bot-token-here
API_BASE_URL=http://localhost:8000
```

### 4. Запустите бота

```bash
python telegram_bot.py
```

Вы должны увидеть:

```
🤖 Запуск Telegram бота...
📡 API: http://localhost:8000
✅ Бот запущен!
Остановка: Ctrl+C
```

## Использование

### Команды бота

- `/start` - Начало работы, главное меню
- `/help` - Справка по использованию
- `/login` - Авторизация
- `/logout` - Выход из аккаунта
- `/skip` - Пропустить добавление фото

### Процесс авторизации

1. Отправьте `/start` или `/login`
2. Нажмите кнопку **"🔑 Войти"** (она запросит контакт)
3. Нажмите **"Поделиться контактом"** - бот получит ваш номер автоматически
4. Получите OTP код (в разработке отображается в сообщении)
5. Введите код
6. ✅ Готово! Вы авторизованы

### Создание метки

1. После авторизации нажмите **"📍 Создать метку"**
2. Отправьте **геолокацию** (кнопка отправки геолокации в Telegram)
3. Выберите **тип метки** (притон, реклама, курьер, употребление, мусор)
4. Выберите **степень опасности** (критично, высокая, средняя, низкая, нейтрально)
5. Отправьте **описание проблемы** текстом
6. По желанию отправьте **фото** или нажмите `/skip`
7. ✅ Метка создана и отправлена на модерацию!

### Просмотр меток рядом

1. Нажмите **"🗺 Метки рядом"**
2. Отправьте **геолокацию**
3. Бот покажет все одобренные метки в радиусе 5 км

### Статистика

Нажмите **"📊 Моя статистика"** чтобы увидеть:
- Общее количество ваших меток
- Активность за сегодня
- Оставшийся дневной лимит

## Особенности

### Кнопка "Поделиться контактом"

Бот автоматически запрашивает ваш номер телефона через специальную кнопку Telegram.

Вам **НЕ нужно** вводить номер вручную - просто нажмите кнопку и Telegram отправит ваш контакт боту.

### OTP коды в разработке

В режиме разработки (когда API использует SQLite), OTP код отображается прямо в сообщении бота для удобства тестирования:

```
✅ OTP код отправлен на +79991234567

🔢 Код (для разработки): 123456

Введите код подтверждения:
```

В продакшене этот код нужно получать из реального SMS.

### Типы меток с эмодзи

- 🏚 **Притон** - места употребления/продажи
- 📢 **Реклама** - объявления о наркотиках
- 🚶 **Курьер** - точки встречи с курьерами
- 💊 **Употребление** - места употребления
- 🗑 **Мусор** - шприцы и другой мусор

### Цветовая кодировка

- 🔴 **Критично** - требует немедленного внимания
- 🟠 **Высокая** - серьёзная проблема
- 🟡 **Средняя** - требует внимания
- 🟢 **Низкая** - незначительная проблема
- ⚪️ **Нейтрально** - для информации

## Архитектура

### Структура кода

```python
# API функции
api_request_otp()       # Запрос OTP кода
api_verify_otp()        # Верификация OTP
api_create_marker()     # Создание метки
api_get_markers()       # Получение меток
api_upload_photo()      # Загрузка фото
api_get_user_stats()    # Статистика

# Клавиатуры
get_main_keyboard()           # Главная клавиатура
get_marker_type_keyboard()    # Выбор типа метки
get_marker_color_keyboard()   # Выбор цвета

# Обработчики
handle_contact()              # Обработка номера телефона
handle_otp_code()            # Обработка OTP кода
handle_location_for_marker() # Обработка геолокации для метки
handle_location_for_nearby() # Обработка геолокации для поиска
handle_marker_photo()        # Обработка фото метки
```

### Состояние (user_data)

Бот хранит состояние для каждого пользователя:

```python
context.user_data = {
    'access_token': 'jwt_token',      # JWT токен
    'refresh_token': 'refresh_token',  # Refresh токен
    'user_id': 1,                      # ID пользователя
    'role': 'user',                    # Роль
    'phone': '+79991234567',           # Номер телефона
    'awaiting': 'otp',                 # Ожидаемое действие
    'marker_lat': 55.7558,             # Координаты метки
    'marker_lon': 37.6173,
    'marker_type': 'den',              # Тип метки
    'marker_color': 'red',             # Цвет метки
    'last_marker_id': 123              # ID последней метки
}
```

## Деплой

### Запуск в фоне (Linux/Mac)

```bash
# С помощью nohup
nohup python telegram_bot.py > bot.log 2>&1 &

# Или с помощью screen
screen -S telegram_bot
python telegram_bot.py
# Нажмите Ctrl+A, затем D для отсоединения
```

### Systemd сервис (Linux)

Создайте файл `/etc/systemd/system/narcomap-bot.service`:

```ini
[Unit]
Description=Narcomap Telegram Bot
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/project
Environment="TELEGRAM_BOT_TOKEN=your-token"
Environment="API_BASE_URL=http://localhost:8000"
ExecStart=/usr/bin/python3 telegram_bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Запустите:

```bash
sudo systemctl daemon-reload
sudo systemctl enable narcomap-bot
sudo systemctl start narcomap-bot
sudo systemctl status narcomap-bot
```

### Docker

Создайте `Dockerfile.bot`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir python-telegram-bot httpx

COPY telegram_bot.py .

CMD ["python", "telegram_bot.py"]
```

Запустите:

```bash
docker build -f Dockerfile.bot -t narcomap-bot .
docker run -d --name narcomap-bot \
  -e TELEGRAM_BOT_TOKEN=your-token \
  -e API_BASE_URL=http://host.docker.internal:8000 \
  narcomap-bot
```

## Troubleshooting

### Бот не отвечает

1. Проверьте что бот запущен
2. Проверьте токен бота
3. Проверьте интернет-соединение
4. Посмотрите логи на ошибки

### API недоступен

```
Ошибка создания метки: Connection refused
```

Решение:
- Убедитесь что API запущен
- Проверьте `API_BASE_URL`
- Проверьте фаервол/порты

### OTP не приходит

В разработке:
- Код отображается в сообщении бота
- Проверьте логи в `logs/otp.log`

В продакшене:
- Проверьте настройки SMS провайдера
- Убедитесь что `SMS_PROVIDER` не `mock`

### Геолокация не работает

- Telegram должен иметь доступ к вашей геолокации
- Попробуйте отправить геолокацию через скрепку → Геопозиция

### Фото не загружается

```
Ошибка загрузки фото
```

Решение:
- Проверьте размер фото (макс 10MB)
- Проверьте формат (JPG, PNG, GIF)
- Убедитесь что API доступен

## Примеры использования

### Пример 1: Простое создание метки

```
1. /start
2. Нажать "🔑 Войти"
3. Поделиться контактом
4. Ввести код: 123456
5. Нажать "📍 Создать метку"
6. Отправить геолокацию
7. Выбрать "🏚 Притон"
8. Выбрать "🔴 Критично"
9. Написать: "Подозрительная активность"
10. /skip (без фото)
```

### Пример 2: С фото

```
1-9. (как в примере 1)
10. Отправить фото
11. ✅ Готово!
```

### Пример 3: Просмотр меток

```
1. Нажать "🗺 Метки рядом"
2. Отправить геолокацию
3. Получить список меток в радиусе 5 км
```

## Дополнительные возможности

### Webhooks вместо polling

Для продакшена рекомендуется использовать webhooks:

```python
# Замените application.run_polling() на:
application.run_webhook(
    listen="0.0.0.0",
    port=8443,
    url_path="telegram_webhook",
    webhook_url=f"https://your-domain.com/telegram_webhook"
)
```

### Мультиязычность

Добавьте поддержку нескольких языков через словари:

```python
TEXTS = {
    'ru': {
        'welcome': 'Добро пожаловать!',
        'login': 'Войти'
    },
    'en': {
        'welcome': 'Welcome!',
        'login': 'Login'
    }
}
```

### Уведомления

Настройте отправку уведомлений пользователям:

```python
async def notify_marker_approved(user_id, marker_id):
    await application.bot.send_message(
        chat_id=user_id,
        text=f"✅ Ваша метка #{marker_id} одобрена!"
    )
```

## Лицензия

MIT
