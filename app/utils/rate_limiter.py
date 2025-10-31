"""
Rate Limiter для защиты от спама и DDoS.

Простая реализация с in-memory хранилищем.
Для продакшена рекомендуется использовать Redis.
"""
from datetime import datetime, timedelta, timezone
from typing import Dict, Tuple
from collections import defaultdict
import threading

from ..config import settings


class RateLimiter:
    """
    In-memory rate limiter.

    Использование:
    ```python
    from fastapi import Request, HTTPException

    rate_limiter = RateLimiter()

    @app.get("/api/endpoint")
    def endpoint(request: Request):
        client_id = request.client.host

        if not rate_limiter.check_rate_limit(client_id, limit=10, window_seconds=60):
            raise HTTPException(status_code=429, detail="Too many requests")

        return {"message": "OK"}
    ```

    Для продакшена с Redis:
    ```python
    import redis
    from datetime import datetime

    redis_client = redis.Redis(host='localhost', port=6379, db=0)

    def check_rate_limit_redis(client_id: str, limit: int, window_seconds: int) -> bool:
        key = f"rate_limit:{client_id}"
        now = datetime.now().timestamp()

        # Используем sorted set для хранения timestamps
        redis_client.zadd(key, {str(now): now})

        # Удаляем старые записи
        redis_client.zremrangebyscore(key, 0, now - window_seconds)

        # Проверяем количество запросов
        count = redis_client.zcard(key)

        # Устанавливаем TTL
        redis_client.expire(key, window_seconds)

        return count <= limit
    ```
    """

    def __init__(self):
        self.requests: Dict[str, list] = defaultdict(list)
        self.lock = threading.Lock()

    def check_rate_limit(
        self,
        client_id: str,
        limit: int = None,
        window_seconds: int = 60
    ) -> bool:
        """
        Проверка rate limit для клиента.

        Args:
            client_id: Идентификатор клиента (IP, user_id и т.д.)
            limit: Макс. количество запросов (если None - из настроек)
            window_seconds: Окно времени в секундах

        Returns:
            True если лимит не превышен, False если превышен
        """
        if limit is None:
            limit = settings.RATE_LIMIT_PER_MINUTE

        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(seconds=window_seconds)

        with self.lock:
            # Получаем список запросов клиента
            client_requests = self.requests[client_id]

            # Удаляем старые запросы
            client_requests = [
                req_time for req_time in client_requests
                if req_time > cutoff
            ]

            # Проверяем лимит
            if len(client_requests) >= limit:
                return False

            # Добавляем текущий запрос
            client_requests.append(now)
            self.requests[client_id] = client_requests

            return True

    def get_remaining(
        self,
        client_id: str,
        limit: int = None,
        window_seconds: int = 60
    ) -> Tuple[int, datetime]:
        """
        Получение оставшегося количества запросов.

        Args:
            client_id: Идентификатор клиента
            limit: Макс. количество запросов
            window_seconds: Окно времени

        Returns:
            (количество оставшихся запросов, время сброса)
        """
        if limit is None:
            limit = settings.RATE_LIMIT_PER_MINUTE

        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(seconds=window_seconds)

        with self.lock:
            client_requests = self.requests.get(client_id, [])
            client_requests = [
                req_time for req_time in client_requests
                if req_time > cutoff
            ]

            remaining = max(0, limit - len(client_requests))

            # Время сброса = самый старый запрос + window
            if client_requests:
                oldest = min(client_requests)
                reset_at = oldest + timedelta(seconds=window_seconds)
            else:
                reset_at = now

            return remaining, reset_at

    def reset(self, client_id: str):
        """
        Сброс rate limit для клиента.

        Args:
            client_id: Идентификатор клиента
        """
        with self.lock:
            if client_id in self.requests:
                del self.requests[client_id]

    def cleanup(self, max_age_seconds: int = 3600):
        """
        Очистка старых записей (периодически вызывайте для экономии памяти).

        Args:
            max_age_seconds: Макс. возраст записей в секундах
        """
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(seconds=max_age_seconds)

        with self.lock:
            # Очистка старых запросов
            for client_id in list(self.requests.keys()):
                client_requests = self.requests[client_id]
                client_requests = [
                    req_time for req_time in client_requests
                    if req_time > cutoff
                ]

                if not client_requests:
                    del self.requests[client_id]
                else:
                    self.requests[client_id] = client_requests


# Singleton instance
rate_limiter = RateLimiter()
