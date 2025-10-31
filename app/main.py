"""
Точка входа FastAPI приложения.

Запуск:
    uvicorn app.main:app --reload

Production:
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
"""
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import os
import time

from .config import settings
from .database import init_db
from .routers import auth, users, markers, moderation, admin, icons
from .utils.rate_limiter import rate_limiter


# Настройка логирования
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(settings.LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# Lifecycle events
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle manager для FastAPI.
    Выполняется при старте и остановке приложения.
    """
    # Startup
    logger.info("Запуск приложения...")

    # Инициализация БД
    init_db()
    logger.info("База данных инициализирована")

    # Создание директорий
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    logger.info(f"Директория загрузок: {settings.UPLOAD_DIR}")

    # Setup webhooks (если нужно)
    # from .adapters.webhooks_adapter import setup_webhooks
    # setup_webhooks()

    logger.info(f"{settings.APP_NAME} v{settings.APP_VERSION} запущен")

    yield

    # Shutdown
    logger.info("Остановка приложения...")


# Создание FastAPI приложения
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
    API для картографирования проблемных точек.

    ## Возможности

    * **Авторизация**: OTP по телефону + JWT токены
    * **Метки**: Создание, просмотр, фильтрация меток на карте
    * **Модерация**: Одобрение/отклонение меток модераторами
    * **Полиция**: Отметка меток как "решено" с отчётами
    * **Админка**: Управление пользователями и ролями

    ## Авторизация

    1. Запросите OTP код: `POST /auth/request-otp`
    2. Подтвердите код: `POST /auth/verify-otp`
    3. Получите JWT токен
    4. Используйте токен в заголовке: `Authorization: Bearer <token>`

    ## RBAC Roles

    * **user**: Может создавать метки
    * **moderator**: Может модерировать метки
    * **police**: Может отмечать метки как решённые
    * **admin**: Полный доступ
    """,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)


# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Rate limiting middleware
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """
    Middleware для rate limiting.
    Ограничивает количество запросов с одного IP.
    """
    # Пропускаем rate limiting для документации
    if request.url.path in ["/docs", "/redoc", "/openapi.json"]:
        return await call_next(request)

    client_ip = request.client.host

    # Проверка лимита
    if not rate_limiter.check_rate_limit(
        client_id=client_ip,
        limit=settings.RATE_LIMIT_PER_MINUTE,
        window_seconds=60
    ):
        remaining, reset_at = rate_limiter.get_remaining(
            client_ip,
            settings.RATE_LIMIT_PER_MINUTE,
            60
        )

        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "detail": "Превышен лимит запросов. Попробуйте позже.",
                "retry_after": int((reset_at - time.time()))
            },
            headers={
                "Retry-After": str(int((reset_at - time.time()))),
                "X-RateLimit-Limit": str(settings.RATE_LIMIT_PER_MINUTE),
                "X-RateLimit-Remaining": str(remaining),
                "X-RateLimit-Reset": reset_at.isoformat()
            }
        )

    response = await call_next(request)

    # Добавляем заголовки rate limit
    remaining, reset_at = rate_limiter.get_remaining(
        client_ip,
        settings.RATE_LIMIT_PER_MINUTE,
        60
    )

    response.headers["X-RateLimit-Limit"] = str(settings.RATE_LIMIT_PER_MINUTE)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    response.headers["X-RateLimit-Reset"] = reset_at.isoformat()

    return response


# Logging middleware
@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """
    Middleware для логирования всех запросов.
    """
    start_time = time.time()

    # Логируем запрос
    logger.info(f"Request: {request.method} {request.url.path}")

    response = await call_next(request)

    # Логируем ответ
    process_time = time.time() - start_time
    logger.info(
        f"Response: {request.method} {request.url.path} "
        f"Status: {response.status_code} "
        f"Time: {process_time:.3f}s"
    )

    return response


# Подключение роутеров
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(markers.router)
app.include_router(moderation.router)
app.include_router(admin.router)
app.include_router(icons.router)


# Статические файлы (uploads)
if os.path.exists(settings.UPLOAD_DIR):
    app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# Статические файлы (web)
web_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "web")
if os.path.exists(web_dir):
    app.mount("/web", StaticFiles(directory=web_dir, html=True), name="web")


# Health check
@app.get("/health", tags=["System"])
def health_check():
    """
    Health check endpoint для мониторинга.

    Используется load balancer'ами и системами мониторинга.
    """
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION
    }


@app.get("/", tags=["System"])
def root():
    """
    Корневой endpoint.
    """
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/health"
    }


# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Обработчик HTTP исключений.
    """
    logger.error(f"HTTP {exc.status_code}: {exc.detail} - {request.method} {request.url.path}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """
    Обработчик общих исключений.
    """
    logger.error(f"Unexpected error: {str(exc)} - {request.method} {request.url.path}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"}
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
