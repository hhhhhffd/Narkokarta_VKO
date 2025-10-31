"""
Webhooks адаптер для интеграции с внешними системами.

Позволяет отправлять события API на внешние endpoints.

События:
- marker.created - новая метка создана
- marker.approved - метка одобрена
- marker.rejected - метка отклонена
- marker.resolved - метка решена полицией
- user.registered - новый пользователь зарегистрирован

Использование:
1. Настройте WEBHOOK_URL в .env
2. Подпишитесь на события через register_webhook()
3. События будут автоматически отправляться на ваш endpoint
"""
import httpx
import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class WebhooksAdapter:
    """
    Адаптер для отправки webhooks на внешние системы.

    Пример использования:

    ```python
    # Инициализация
    webhooks = WebhooksAdapter()

    # Регистрация webhook endpoint
    webhooks.register_webhook(
        event="marker.created",
        url="https://your-app.com/webhooks/marker-created",
        secret="your-secret-key"  # Для подписи HMAC
    )

    # Отправка события
    webhooks.send_event(
        event="marker.created",
        data={
            "marker_id": 123,
            "title": "Новая метка",
            "latitude": 55.7558,
            "longitude": 37.6173,
            "created_by": 1
        }
    )
    ```

    Формат webhook запроса:
    ```
    POST https://your-app.com/webhooks/marker-created
    Headers:
        Content-Type: application/json
        X-Webhook-Event: marker.created
        X-Webhook-Signature: sha256=...
        X-Webhook-Timestamp: 2025-10-30T10:00:00Z
    Body:
        {
            "event": "marker.created",
            "timestamp": "2025-10-30T10:00:00Z",
            "data": {
                "marker_id": 123,
                ...
            }
        }
    ```

    Пример обработчика webhook (FastAPI):
    ```python
    @app.post("/webhooks/marker-created")
    async def handle_marker_created(request: Request):
        # Получаем данные
        payload = await request.json()
        event = payload["event"]
        data = payload["data"]

        # Проверяем подпись
        signature = request.headers.get("X-Webhook-Signature")
        if not verify_signature(payload, signature, secret="your-secret-key"):
            raise HTTPException(status_code=401, detail="Invalid signature")

        # Обрабатываем событие
        if event == "marker.created":
            marker_id = data["marker_id"]
            print(f"Новая метка создана: {marker_id}")

        return {"status": "ok"}
    ```
    """

    def __init__(self):
        self.webhooks: Dict[str, List[Dict[str, str]]] = {}
        self.client = httpx.AsyncClient(timeout=10.0)

    def register_webhook(self, event: str, url: str, secret: Optional[str] = None):
        """
        Регистрация webhook endpoint для события.

        Args:
            event: Название события (marker.created, marker.approved и т.д.)
            url: URL endpoint для отправки
            secret: Секретный ключ для HMAC подписи (опционально)
        """
        if event not in self.webhooks:
            self.webhooks[event] = []

        self.webhooks[event].append({
            "url": url,
            "secret": secret or ""
        })

        logger.info(f"Webhook зарегистрирован: {event} -> {url}")

    async def send_event(self, event: str, data: Dict[str, Any]) -> bool:
        """
        Отправка события на зарегистрированные webhooks.

        Args:
            event: Название события
            data: Данные события

        Returns:
            True если успешно отправлено хотя бы на один endpoint
        """
        if event not in self.webhooks or not self.webhooks[event]:
            logger.debug(f"Нет зарегистрированных webhooks для события: {event}")
            return False

        timestamp = datetime.now(timezone.utc).isoformat() + "Z"
        payload = {
            "event": event,
            "timestamp": timestamp,
            "data": data
        }

        success_count = 0

        for webhook in self.webhooks[event]:
            url = webhook["url"]
            secret = webhook["secret"]

            # Генерация подписи
            signature = self._generate_signature(payload, secret) if secret else None

            # Заголовки
            headers = {
                "Content-Type": "application/json",
                "X-Webhook-Event": event,
                "X-Webhook-Timestamp": timestamp
            }

            if signature:
                headers["X-Webhook-Signature"] = signature

            # Отправка
            try:
                response = await self.client.post(
                    url,
                    headers=headers,
                    json=payload
                )

                if response.status_code in [200, 201, 202, 204]:
                    logger.info(f"Webhook отправлен: {event} -> {url} ({response.status_code})")
                    success_count += 1
                else:
                    logger.error(f"Ошибка webhook: {event} -> {url} ({response.status_code})")

            except Exception as e:
                logger.error(f"Ошибка отправки webhook {event} -> {url}: {str(e)}")

        return success_count > 0

    def _generate_signature(self, payload: Dict[str, Any], secret: str) -> str:
        """
        Генерация HMAC SHA256 подписи.

        Args:
            payload: Данные для подписи
            secret: Секретный ключ

        Returns:
            Подпись в формате sha256=...
        """
        import hmac
        import hashlib

        payload_bytes = json.dumps(payload, sort_keys=True).encode('utf-8')
        signature = hmac.new(
            secret.encode('utf-8'),
            payload_bytes,
            hashlib.sha256
        ).hexdigest()

        return f"sha256={signature}"

    async def close(self):
        """Закрытие HTTP клиента"""
        await self.client.aclose()


# Глобальный экземпляр
webhooks_adapter = WebhooksAdapter()


# Хелперы для отправки событий
async def notify_marker_created(marker_data: Dict[str, Any]):
    """Уведомление о создании метки"""
    await webhooks_adapter.send_event("marker.created", marker_data)


async def notify_marker_approved(marker_id: int, moderator_id: int):
    """Уведомление об одобрении метки"""
    await webhooks_adapter.send_event("marker.approved", {
        "marker_id": marker_id,
        "moderator_id": moderator_id
    })


async def notify_marker_rejected(marker_id: int, moderator_id: int, reason: Optional[str] = None):
    """Уведомление об отклонении метки"""
    await webhooks_adapter.send_event("marker.rejected", {
        "marker_id": marker_id,
        "moderator_id": moderator_id,
        "reason": reason
    })


async def notify_marker_resolved(marker_id: int, police_id: int, report: Optional[str] = None):
    """Уведомление о решении метки"""
    await webhooks_adapter.send_event("marker.resolved", {
        "marker_id": marker_id,
        "police_id": police_id,
        "report": report
    })


async def notify_user_registered(user_id: int, phone: str, role: str):
    """Уведомление о регистрации пользователя"""
    await webhooks_adapter.send_event("user.registered", {
        "user_id": user_id,
        "phone": phone,
        "role": role
    })


# Пример конфигурации webhooks
def setup_webhooks():
    """
    Настройка webhooks при старте приложения.

    Вызовите эту функцию в main.py при инициализации.
    """
    # Пример: интеграция с внешней системой мониторинга
    webhooks_adapter.register_webhook(
        event="marker.created",
        url="https://monitoring.example.com/api/webhooks/marker-created",
        secret="your-monitoring-secret"
    )

    # Пример: интеграция с аналитикой
    webhooks_adapter.register_webhook(
        event="marker.approved",
        url="https://analytics.example.com/api/events",
        secret="your-analytics-secret"
    )

    # Пример: уведомления в Slack
    webhooks_adapter.register_webhook(
        event="marker.resolved",
        url="https://hooks.slack.com/services/YOUR/WEBHOOK/URL",
        secret=None  # Slack webhooks не требуют подписи
    )

    logger.info("Webhooks настроены")
