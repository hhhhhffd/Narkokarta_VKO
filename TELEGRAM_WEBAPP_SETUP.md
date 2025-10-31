# Настройка Telegram WebApp

Полная инструкция по подключению интерактивной карты к вашему Telegram боту.

## 🚀 Быстрый старт

### 1. Запустите сервер

```bash
cd "Хакатун карта наркоманов"
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 2. Запустите Telegram бота

```bash
# Установите переменные окружения
export TELEGRAM_BOT_TOKEN="your_bot_token_from_botfather"
export API_BASE_URL="http://localhost:8000"
export WEBAPP_URL="http://localhost:8000/web/index.html"

# Запустите бота
python telegram_bot.py
```

### 3. Протестируйте локально

1. Откройте бота в Telegram
2. Нажмите кнопку **"🗺 Открыть карту"**
3. WebApp откроется в Telegram

> **Примечание**: Для локального тестирования используйте ngrok или другой туннель для получения HTTPS URL.

---

## 📝 Настройка бота через BotFather

### Шаг 1: Создайте или обновите бота

1. Откройте [@BotFather](https://t.me/BotFather) в Telegram
2. Если у вас нет бота:
   - Отправьте `/newbot`
   - Введите имя бота
   - Введите username (должен заканчиваться на "bot")
3. Скопируйте токен бота

### Шаг 2: Настройте команды бота

Отправьте `/setcommands` в BotFather и выберите вашего бота.

Вставьте следующие команды:

```
start - Главное меню
map - Открыть интерактивную карту
help - Справка и инструкции
logout - Выйти из аккаунта
```

### Шаг 3: Настройте описание

```
/setdescription
```

Пример описания:
```
🗺 Наркокарта - сервис картографирования проблемных точек

Возможности:
• Интерактивная карта с кластеризацией
• Создание меток с геолокацией
• Фильтрация по типу и опасности
• Загрузка фото
• Модерация контента

Все метки проходят проверку перед публикацией.
```

### Шаг 4: Настройте короткое описание

```
/setshortdescription
```

Пример:
```
Интерактивная карта проблемных точек с геолокацией и фото
```

---

## 🌐 Деплой на production

### Вариант 1: VPS с доменом

#### 1. Настройте сервер

```bash
# Установите зависимости
sudo apt update
sudo apt install python3-pip nginx certbot python3-certbot-nginx

# Клонируйте проект
git clone <your-repo>
cd "Хакатун карта наркоманов"

# Установите зависимости Python
pip3 install -r requirements.txt
```

#### 2. Получите SSL сертификат

```bash
sudo certbot --nginx -d yourdomain.com
```

#### 3. Настройте Nginx

```nginx
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    # API
    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /markers {
        proxy_pass http://127.0.0.1:8000/markers;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /auth {
        proxy_pass http://127.0.0.1:8000/auth;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /users {
        proxy_pass http://127.0.0.1:8000/users;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /image {
        proxy_pass http://127.0.0.1:8000/image;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # WebApp
    location /web {
        proxy_pass http://127.0.0.1:8000/web;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Uploads
    location /uploads {
        proxy_pass http://127.0.0.1:8000/uploads;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

#### 4. Создайте systemd сервис

**API сервер** (`/etc/systemd/system/narcomap-api.service`):

```ini
[Unit]
Description=Narcomap API
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/var/www/narcomap
Environment="PATH=/var/www/narcomap/.venv/bin"
Environment="TELEGRAM_BOT_TOKEN=your_token"
Environment="API_BASE_URL=https://yourdomain.com"
Environment="WEBAPP_URL=https://yourdomain.com/web/index.html"
ExecStart=/var/www/narcomap/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

**Telegram бот** (`/etc/systemd/system/narcomap-bot.service`):

```ini
[Unit]
Description=Narcomap Telegram Bot
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/var/www/narcomap
Environment="PATH=/var/www/narcomap/.venv/bin"
Environment="TELEGRAM_BOT_TOKEN=your_token"
Environment="API_BASE_URL=https://yourdomain.com"
Environment="WEBAPP_URL=https://yourdomain.com/web/index.html"
ExecStart=/var/www/narcomap/.venv/bin/python telegram_bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```

#### 5. Запустите сервисы

```bash
sudo systemctl daemon-reload
sudo systemctl enable narcomap-api narcomap-bot
sudo systemctl start narcomap-api narcomap-bot

# Проверка статуса
sudo systemctl status narcomap-api
sudo systemctl status narcomap-bot
```

#### 6. Обновите переменные окружения

```bash
# В .env файле
TELEGRAM_BOT_TOKEN=your_bot_token
API_BASE_URL=https://yourdomain.com
WEBAPP_URL=https://yourdomain.com/web/index.html
```

### Вариант 2: Ngrok (для тестирования)

Если у вас нет домена, используйте ngrok для тестирования:

```bash
# Установите ngrok
brew install ngrok  # macOS
# или скачайте с https://ngrok.com/download

# Запустите туннель
ngrok http 8000

# Скопируйте HTTPS URL (например, https://abc123.ngrok.io)
```

Обновите переменные:

```bash
export WEBAPP_URL="https://abc123.ngrok.io/web/index.html"
```

---

## 🎨 Интерфейс в Telegram

### Главная клавиатура

Кнопки доступные пользователям:

**Неавторизованные:**
- 🗺 Открыть карту (WebApp)
- 🔑 Войти

**Авторизованные:**
- 🗺 Открыть карту (WebApp)
- 📍 Создать метку
- 🗺 Метки рядом
- 📊 Моя статистика
- ℹ️ Помощь | 🚪 Выйти

### Команды

- `/start` - Главное меню с приветствием
- `/map` - Кнопка для открытия карты
- `/help` - Подробная справка
- `/logout` - Выход из аккаунта

---

## 🔧 Конфигурация

### Переменные окружения

Создайте файл `.env`:

```bash
# Telegram Bot
TELEGRAM_BOT_TOKEN=your_bot_token_here

# API URLs
API_BASE_URL=https://yourdomain.com
WEBAPP_URL=https://yourdomain.com/web/index.html

# Database
DATABASE_URL=sqlite:///./narcomap.db

# JWT
JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=1440

# App
APP_NAME=Наркокарта
DEBUG=False
```

### В telegram_bot.py

```python
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN")
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
WEBAPP_URL = os.getenv("WEBAPP_URL", "http://localhost:8000/web/index.html")
```

---

## 📱 Работа WebApp

### Что происходит при открытии карты

1. Пользователь нажимает "🗺 Открыть карту"
2. Telegram открывает WebApp по URL `WEBAPP_URL`
3. Загружается `index.html` с картой
4. JavaScript инициализирует:
   - MapLibre GL с OpenFreeMap
   - Telegram WebApp SDK
   - Загрузку меток через API
   - Кластеризацию меток

### Возможности WebApp

- ✅ Просмотр всех одобренных меток
- ✅ Кластеризация близких меток
- ✅ Фильтрация по типу и цвету
- ✅ Создание меток кликом
- ✅ Просмотр фото и описаний
- ✅ Геолокация пользователя
- ✅ Авторизация через localStorage

### Интеграция с Telegram

```javascript
// В app.js
if (window.Telegram && window.Telegram.WebApp) {
    const tg = window.Telegram.WebApp;
    tg.ready();
    tg.expand();

    // Кнопка "Назад"
    tg.BackButton.show();
    tg.BackButton.onClick(() => {
        // Закрыть или вернуться
    });
}
```

---

## 🐛 Troubleshooting

### WebApp не открывается

**Проблема**: При нажатии кнопки ничего не происходит

**Решения**:
1. Проверьте, что используется **HTTPS** (обязательно для WebApp)
2. Убедитесь, что URL доступен публично
3. Проверьте в логах сервера доступность `/web/index.html`

```bash
# Проверка доступности
curl https://yourdomain.com/web/index.html
```

### Карта не загружается в WebApp

**Проблема**: Белый экран или ошибка загрузки

**Решения**:
1. Откройте консоль в DevTools Telegram Desktop
2. Проверьте CORS заголовки в `app/main.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене укажите конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### API недоступен из WebApp

**Проблема**: Метки не загружаются

**Решения**:
1. В `web/app.js` проверьте `API_BASE_URL`:

```javascript
const CONFIG = {
    API_BASE_URL: window.location.origin,  // Используйте тот же домен
    // ...
};
```

2. Убедитесь, что API endpoints доступны:

```bash
curl https://yourdomain.com/markers?status=approved
```

### Иконки не отображаются

**Проблема**: Метки без иконок

**Решения**:
1. Проверьте endpoints `/image/icon1-6`:

```bash
curl https://yourdomain.com/image/icon1
```

2. Убедитесь, что роутер `icons.py` подключен в `main.py`

### Telegram выдает ошибку "WebApp URL is invalid"

**Проблема**: URL не принимается

**Причины**:
- URL должен быть HTTPS (кроме localhost для тестирования)
- URL должен быть публично доступен
- URL должен начинаться с `https://` или `http://` (для localhost)

---

## 📊 Мониторинг

### Логи

```bash
# API логи
sudo journalctl -u narcomap-api -f

# Bot логи
sudo journalctl -u narcomap-bot -f

# Nginx логи
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### Метрики

Для продакшена рекомендуется настроить:
- **Prometheus** + **Grafana** для мониторинга
- **Sentry** для отслеживания ошибок
- **PM2** или **Supervisor** для управления процессами

---

## 🔒 Безопасность

### Рекомендации

1. **HTTPS**: Обязательно используйте HTTPS
2. **Секреты**: Храните токены в переменных окружения
3. **CORS**: Ограничьте allowed origins
4. **Rate Limiting**: Настроен в `app/main.py`
5. **JWT**: Используйте сложный SECRET_KEY

### Пример .env для production

```bash
# НЕ коммитьте этот файл!
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
JWT_SECRET_KEY=$(openssl rand -hex 32)
DATABASE_URL=postgresql://user:pass@localhost/narcomap
DEBUG=False
```

---

## 📚 Дополнительные ресурсы

- [Telegram WebApp Documentation](https://core.telegram.org/bots/webapps)
- [MapLibre GL Documentation](https://maplibre.org/maplibre-gl-js/docs/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [python-telegram-bot Documentation](https://docs.python-telegram-bot.org/)

---

## ✅ Чеклист запуска

- [ ] Создан бот через BotFather
- [ ] Настроены команды бота
- [ ] Получен SSL сертификат (для production)
- [ ] Настроен Nginx (для production)
- [ ] Настроены systemd сервисы
- [ ] Установлены переменные окружения
- [ ] API сервер запущен и доступен
- [ ] Telegram бот запущен
- [ ] WebApp открывается в Telegram
- [ ] Карта корректно загружается
- [ ] Метки отображаются
- [ ] Кластеризация работает
- [ ] Можно создавать новые метки

---

Готово! 🎉 Ваш Telegram WebApp с интерактивной картой настроен и готов к использованию.
