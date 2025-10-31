# Наркокарта

Полнофункциональная система картографирования проблемных точек с API, веб-приложением и Telegram ботом.

## 🚀 Компоненты системы

### 1. 🔧 API Backend (FastAPI)
Портируемый REST API с полной бизнес-логикой

### 2. 🌐 Веб-приложение
Интерактивная карта с метками на базе Leaflet

### 3. 🤖 Telegram Бот
Удобный бот с кнопкой "Поделиться контактом"

## ✨ Возможности

- **Авторизация**: OTP по номеру телефона + JWT токены
- **Метки**: Создание, просмотр, фильтрация меток на карте с геолокацией
- **Модерация**: Система одобрения/отклонения меток модераторами
- **Полиция**: Отметка меток как "решено" с отчётами и фото
- **RBAC**: Ролевая модель (user, moderator, police, admin)
- **Портируемость**: Веб, Telegram, мобильные приложения, десктоп
- **Масштабируемость**: Готов к миграции на PostgreSQL, Redis, S3

## 🛠 Технологии

- **Backend**: Python 3.11, FastAPI
- **Database**: SQLite (разработка) / PostgreSQL (продакшен)
- **Auth**: JWT, OTP через SMS
- **Web**: HTML5, CSS3, Leaflet, Vanilla JS
- **Bot**: python-telegram-bot
- **Testing**: pytest
- **Deployment**: Docker, docker-compose

## Быстрый старт

### Локальный запуск

```bash
# Клонирование репозитория
git clone <repo-url>
cd narcomap

# Создание виртуального окружения
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Установка зависимостей
pip install -r requirements.txt

# Генерация секретных ключей
python scripts/generate_keys.py

# Копирование .env.example в .env и заполнение переменных
cp .env.example .env
# Отредактируйте .env, добавьте сгенерированный JWT_SECRET_KEY

# Инициализация БД
python scripts/init_db.py

# Запуск сервера
uvicorn app.main:app --reload

# API доступен на http://localhost:8000
# Документация: http://localhost:8000/docs
```

### Docker запуск

```bash
# Сборка и запуск
docker-compose up --build

# В фоне
docker-compose up -d

# Остановка
docker-compose down
```

### 🌐 Запуск веб-приложения

```bash
# Перейдите в папку web
cd web

# Запустите HTTP сервер (Python)
python -m http.server 8080

# Или используйте Node.js
npm install -g http-server
http-server -p 8080

# Откройте в браузере
open http://localhost:8080
```

См. [web/README.md](web/README.md) для подробностей.

### 🤖 Запуск Telegram бота

```bash
# Установите зависимости
pip install python-telegram-bot httpx

# Создайте бота через @BotFather и получите токен

# Установите переменную окружения
export TELEGRAM_BOT_TOKEN="your-bot-token-here"

# Запустите бота
python telegram_bot.py
```

См. [TELEGRAM_BOT.md](TELEGRAM_BOT.md) для подробной инструкции.

## 📱 Быстрый старт для пользователей

### Вариант 1: Веб-приложение

1. Откройте http://localhost:8080 в браузере
2. Нажмите "Войти"
3. Введите номер телефона → получите код
4. Кликните на карту → создайте метку

### Вариант 2: Telegram бот

1. Найдите бота в Telegram
2. Отправьте `/start`
3. Нажмите "🔑 Войти" → поделитесь контактом
4. Введите код → готово!
5. Отправьте геолокацию → создайте метку
```

## Структура проекта

```
narcomap/
├── app/
│   ├── main.py                      # FastAPI приложение
│   ├── config.py                    # Конфигурация
│   ├── database.py                  # Подключение к БД
│   ├── models.py                    # SQLAlchemy модели
│   ├── auth/                        # Авторизация (JWT, OTP, RBAC)
│   ├── services/                    # Бизнес-логика
│   ├── routers/                     # API endpoints
│   ├── adapters/                    # Интеграции (SMS, Telegram, Push, Webhooks)
│   └── utils/                       # Валидация, rate limiting
├── tests/                           # Тесты
├── scripts/                         # Утилиты
├── uploads/                         # Медиа файлы
└── logs/                           # Логи (включая OTP коды)
```

## Конфигурация

Все настройки задаются через переменные окружения в `.env` файле.

### Основные переменные

```bash
# Database
DATABASE_URL=sqlite:///./narcomap.db  # Или postgresql://...

# JWT
JWT_SECRET_KEY=<generated-secret>     # Генерируется через generate_keys.py
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
JWT_REFRESH_TOKEN_EXPIRE_DAYS=30

# OTP
OTP_EXPIRE_MINUTES=5
OTP_LENGTH=6
OTP_LOG_FILE=./logs/otp.log          # ВАЖНО: Логи OTP кодов (только для разработки!)

# SMS Provider
SMS_PROVIDER=mock                     # mock | twilio | smsru | custom
# SMS_API_KEY=your-key                # Для продакшена
# SMS_API_URL=https://...             # Для кастомного провайдера

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_PER_HOUR=1000

# Media
UPLOAD_DIR=./uploads
MAX_UPLOAD_SIZE_MB=10
USE_S3=False                          # True для продакшена
```

См. `.env.example` для полного списка переменных.

## Авторизация

### Процесс OTP + JWT

1. **Запрос OTP кода**

```bash
curl -X POST http://localhost:8000/auth/request-otp \
  -H "Content-Type: application/json" \
  -d '{"phone": "+79991234567"}'

# Response: {"success": true, "message": "OTP код отправлен", "code": "123456"}
# Код также логируется в logs/otp.log
```

2. **Верификация OTP**

```bash
curl -X POST http://localhost:8000/auth/verify-otp \
  -H "Content-Type: application/json" \
  -d '{"phone": "+79991234567", "code": "123456"}'

# Response: {
#   "access_token": "eyJhbGci...",
#   "refresh_token": "eyJhbGci...",
#   "user_id": 1,
#   "role": "user"
# }
```

3. **Использование токена**

```bash
curl http://localhost:8000/users/me \
  -H "Authorization: Bearer eyJhbGci..."
```

### OTP коды в разработке

В режиме разработки (SQLite) OTP коды логируются в `logs/otp.log` в формате:

```
2025-10-30 10:00:00 - OTP for +79991234567: 123456
```

**ВАЖНО**: В продакшене обязательно отключите логирование OTP кодов!

## API Endpoints

### Authentication

- `POST /auth/request-otp` - Запрос OTP кода
- `POST /auth/verify-otp` - Верификация OTP и получение JWT
- `POST /auth/refresh` - Обновление access токена

### Users

- `GET /users/me` - Профиль текущего пользователя
- `GET /users/me/stats` - Статистика пользователя
- `PATCH /users/me` - Обновление профиля

### Markers

- `POST /markers` - Создание метки
- `GET /markers` - Список меток с фильтрацией
- `GET /markers/{id}` - Получение метки
- `PATCH /markers/{id}` - Обновление метки
- `DELETE /markers/{id}` - Удаление метки
- `POST /markers/{id}/photo` - Загрузка фото
- `GET /markers/stats` - Статистика меток

### Moderation (требует роль moderator+)

- `GET /moderation/pending` - Метки на модерации
- `POST /moderation/{id}/approve` - Одобрить метку
- `POST /moderation/{id}/reject` - Отклонить метку
- `POST /moderation/{id}/resolve` - Отметить как решено (police)
- `GET /moderation/{id}/history` - История модерации
- `GET /moderation/stats/me` - Статистика модератора

### Admin (требует роль admin)

- `GET /admin/users` - Список пользователей
- `GET /admin/users/{id}` - Пользователь по ID
- `PATCH /admin/users/{id}` - Обновление пользователя
- `DELETE /admin/users/{id}` - Удаление пользователя

Полная документация: `http://localhost:8000/docs`

## Тестирование

```bash
# Запуск всех тестов
pytest

# С покрытием
pytest --cov=app --cov-report=html

# Конкретные тесты
pytest tests/test_auth.py
pytest tests/test_markers.py
pytest tests/test_moderation.py

# Просмотр покрытия
open htmlcov/index.html
```

## Миграция на PostgreSQL

1. Установите PostgreSQL
2. Создайте базу данных:

```sql
CREATE DATABASE narcomap;
CREATE USER narcomap WITH PASSWORD 'secure-password';
GRANT ALL PRIVILEGES ON DATABASE narcomap TO narcomap;
```

3. Обновите `.env`:

```bash
DATABASE_URL=postgresql://narcomap:secure-password@localhost:5432/narcomap
```

4. Запустите `python scripts/init_db.py`

## Интеграция SMS провайдеров

### Twilio

```bash
# .env
SMS_PROVIDER=twilio
SMS_API_KEY=ACxxxxx:auth_token
```

### SMS.ru

```bash
# .env
SMS_PROVIDER=smsru
SMS_API_KEY=your-api-key
```

### Кастомный провайдер

```bash
# .env
SMS_PROVIDER=custom
SMS_API_KEY=your-api-key
SMS_API_URL=https://api.provider.com/send
```

См. `app/adapters/sms_adapter.py` для деталей.

## Production деплой

### Контрольный список

- [ ] Сгенерируйте надёжный `JWT_SECRET_KEY`
- [ ] Переключитесь на PostgreSQL
- [ ] Настройте реальный SMS провайдер (`SMS_PROVIDER != mock`)
- [ ] **ОТКЛЮЧИТЕ** логирование OTP кодов (удалите/закомментируйте в `app/auth/otp.py`)
- [ ] Настройте S3 для медиа (`USE_S3=True`)
- [ ] Добавьте Redis для rate limiting
- [ ] Настройте CORS (`CORS_ORIGINS`)
- [ ] Включите HTTPS
- [ ] Настройте мониторинг (`/health` endpoint)
- [ ] Настройте логирование (ELK, Sentry)

### Docker Production

```bash
# .env
DEBUG=False
DATABASE_URL=postgresql://...
SMS_PROVIDER=twilio
USE_S3=True

# docker-compose.yml - раскомментируйте db, redis, nginx

docker-compose up -d
```

### Масштабирование

```bash
# Запуск нескольких worker'ов
docker-compose up --scale api=4
```

## Безопасность

- ✅ JWT токены с истечением
- ✅ OTP коды с истечением
- ✅ RBAC система
- ✅ Rate limiting (60 req/min по умолчанию)
- ✅ Валидация входных данных
- ✅ CORS настройки
- ✅ Anti-spam (лимиты на создание меток)
- ✅ Геолокационная проверка на дубликаты
- ⚠️ OTP логирование (только для разработки!)

## Примеры интеграции

См. файлы:
- `API_EXAMPLES.md` - cURL примеры для всех endpoints
- `INTEGRATION_GUIDE.md` - Интеграция с Telegram, мобильными приложениями, десктопом

## Лицензия

MIT

## Поддержка

Для вопросов и предложений создавайте issues в репозитории.
