"""
Mobile Push Notifications адаптер.

Поддерживает отправку push-уведомлений на мобильные устройства через:
- Firebase Cloud Messaging (FCM) для Android/iOS
- Apple Push Notification Service (APNS) для iOS

Использование:
1. Установите firebase-admin: pip install firebase-admin
2. Получите service account key от Firebase
3. Сохраните в firebase-credentials.json
4. Вызывайте send_push() для отправки уведомлений
"""
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class MobilePushAdapter:
    """
    Адаптер для отправки push-уведомлений.

    Пример использования:

    ```python
    # Инициализация
    push_adapter = MobilePushAdapter(
        fcm_credentials_path="firebase-credentials.json"
    )

    # Отправка уведомления одному устройству
    push_adapter.send_push(
        device_token="device_fcm_token",
        title="Метка одобрена",
        body="Ваша метка была одобрена модератором",
        data={"marker_id": 123, "action": "approved"}
    )

    # Отправка уведомлений нескольким устройствам
    push_adapter.send_push_multicast(
        device_tokens=["token1", "token2", "token3"],
        title="Новая метка рядом",
        body="Обнаружена новая метка в радиусе 1 км",
        data={"marker_id": 456, "distance_km": 0.5}
    )
    ```

    Интеграция с мобильным приложением:

    Android (Kotlin):
    ```kotlin
    // В MainActivity.kt или FCM service
    FirebaseMessaging.getInstance().token.addOnCompleteListener { task ->
        if (task.isSuccessful) {
            val token = task.result
            // Отправьте token на сервер при авторизации
            sendTokenToServer(token)
        }
    }

    fun sendTokenToServer(fcmToken: String) {
        // PATCH /users/me с полем fcm_token
        apiService.updateUser(UserUpdate(fcm_token = fcmToken))
    }
    ```

    iOS (Swift):
    ```swift
    // В AppDelegate
    func application(_ application: UIApplication,
                    didRegisterForRemoteNotificationsWithDeviceToken deviceToken: Data) {
        let token = deviceToken.map { String(format: "%02.2hhx", $0) }.joined()
        // Отправьте token на сервер
        sendTokenToServer(token: token)
    }
    ```
    """

    def __init__(self, fcm_credentials_path: Optional[str] = None):
        self.fcm_credentials_path = fcm_credentials_path
        self.fcm_app = None

        if fcm_credentials_path:
            try:
                import firebase_admin
                from firebase_admin import credentials

                cred = credentials.Certificate(fcm_credentials_path)
                self.fcm_app = firebase_admin.initialize_app(cred)
                logger.info("Firebase Admin инициализирован")
            except ImportError:
                logger.warning("firebase-admin не установлен: pip install firebase-admin")
            except Exception as e:
                logger.error(f"Ошибка инициализации Firebase: {str(e)}")

    def send_push(
        self,
        device_token: str,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Отправка push-уведомления одному устройству.

        Args:
            device_token: FCM токен устройства
            title: Заголовок уведомления
            body: Текст уведомления
            data: Дополнительные данные (dict)

        Returns:
            True если успешно, False если ошибка
        """
        if not self.fcm_app:
            logger.warning("Firebase не настроен, уведомление не отправлено (mock)")
            print(f"[MOCK PUSH] To: {device_token}, Title: {title}, Body: {body}, Data: {data}")
            return True

        try:
            from firebase_admin import messaging

            message = messaging.Message(
                notification=messaging.Notification(
                    title=title,
                    body=body
                ),
                data=data or {},
                token=device_token
            )

            response = messaging.send(message)
            logger.info(f"Push отправлен: {response}")
            return True

        except Exception as e:
            logger.error(f"Ошибка отправки push: {str(e)}")
            return False

    def send_push_multicast(
        self,
        device_tokens: List[str],
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, int]:
        """
        Отправка push-уведомлений нескольким устройствам.

        Args:
            device_tokens: Список FCM токенов
            title: Заголовок
            body: Текст
            data: Дополнительные данные

        Returns:
            {"success_count": int, "failure_count": int}
        """
        if not self.fcm_app:
            logger.warning("Firebase не настроен, уведомления не отправлены (mock)")
            print(f"[MOCK PUSH MULTICAST] To: {len(device_tokens)} devices, Title: {title}")
            return {"success_count": len(device_tokens), "failure_count": 0}

        try:
            from firebase_admin import messaging

            message = messaging.MulticastMessage(
                notification=messaging.Notification(
                    title=title,
                    body=body
                ),
                data=data or {},
                tokens=device_tokens
            )

            response = messaging.send_multicast(message)
            logger.info(f"Multicast push отправлен: {response.success_count} успешно, {response.failure_count} ошибок")

            return {
                "success_count": response.success_count,
                "failure_count": response.failure_count
            }

        except Exception as e:
            logger.error(f"Ошибка отправки multicast push: {str(e)}")
            return {"success_count": 0, "failure_count": len(device_tokens)}


# Пример использования для уведомлений о модерации
def notify_marker_approved(user_fcm_token: str, marker_id: int):
    """Уведомление о одобрении метки"""
    adapter = MobilePushAdapter()
    adapter.send_push(
        device_token=user_fcm_token,
        title="Метка одобрена ✅",
        body="Ваша метка прошла модерацию и теперь видна на карте",
        data={
            "type": "marker_approved",
            "marker_id": str(marker_id)
        }
    )


def notify_marker_rejected(user_fcm_token: str, marker_id: int, reason: Optional[str] = None):
    """Уведомление об отклонении метки"""
    adapter = MobilePushAdapter()
    body = f"Ваша метка была отклонена. Причина: {reason}" if reason else "Ваша метка была отклонена модератором"

    adapter.send_push(
        device_token=user_fcm_token,
        title="Метка отклонена ❌",
        body=body,
        data={
            "type": "marker_rejected",
            "marker_id": str(marker_id),
            "reason": reason or ""
        }
    )


def notify_nearby_markers(user_fcm_token: str, count: int):
    """Уведомление о новых метках рядом"""
    adapter = MobilePushAdapter()
    adapter.send_push(
        device_token=user_fcm_token,
        title="Новые метки рядом",
        body=f"Обнаружено {count} новых меток в вашем районе",
        data={
            "type": "nearby_markers",
            "count": str(count)
        }
    )
