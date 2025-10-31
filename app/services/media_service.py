"""
Сервис для работы с медиа-файлами (фото).
Поддерживает локальное хранилище и S3-совместимые облака.
"""
import os
import uuid
from typing import Optional, BinaryIO
from pathlib import Path
from PIL import Image

from ..config import settings


class MediaService:
    """
    Абстрактный сервис для работы с медиа.
    Автоматически выбирает между локальным хранилищем и S3.
    """

    def __init__(self):
        self.use_s3 = settings.USE_S3
        self.upload_dir = settings.UPLOAD_DIR
        self.max_size_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        self.allowed_extensions = settings.allowed_extensions_list

        # Создаём директорию для загрузок если её нет
        if not self.use_s3:
            os.makedirs(self.upload_dir, exist_ok=True)

    def validate_file(self, filename: str, file_size: int) -> tuple[bool, Optional[str]]:
        """
        Валидация файла.

        Args:
            filename: Имя файла
            file_size: Размер файла в байтах

        Returns:
            (валиден ли файл, сообщение об ошибке)
        """
        # Проверка расширения
        ext = Path(filename).suffix.lower()
        if ext not in self.allowed_extensions:
            return False, f"Недопустимое расширение. Разрешены: {', '.join(self.allowed_extensions)}"

        # Проверка размера
        if file_size > self.max_size_bytes:
            return False, f"Файл слишком большой. Макс. размер: {settings.MAX_UPLOAD_SIZE_MB}MB"

        return True, None

    def generate_filename(self, original_filename: str) -> str:
        """
        Генерация уникального имени файла.

        Args:
            original_filename: Оригинальное имя файла

        Returns:
            Уникальное имя вида: uuid_extension
        """
        ext = Path(original_filename).suffix.lower()
        unique_id = uuid.uuid4()
        return f"{unique_id}{ext}"

    def save_file(self, file: BinaryIO, filename: str) -> str:
        """
        Сохранение файла.

        Args:
            file: Файловый объект
            filename: Имя файла (уже сгенерированное через generate_filename)

        Returns:
            URL или путь к сохранённому файлу

        Для локального хранилища: /uploads/filename
        Для S3: https://bucket.s3.amazonaws.com/filename
        """
        if self.use_s3:
            return self._save_to_s3(file, filename)
        else:
            return self._save_locally(file, filename)

    def _save_locally(self, file: BinaryIO, filename: str) -> str:
        """Сохранение в локальную директорию"""
        file_path = os.path.join(self.upload_dir, filename)

        with open(file_path, "wb") as f:
            f.write(file.read())

        # Возвращаем относительный путь для URL
        return f"/uploads/{filename}"

    def _save_to_s3(self, file: BinaryIO, filename: str) -> str:
        """
        Сохранение в S3 хранилище.

        Примечание: требует установки boto3 и настройки credentials.
        Пример интеграции оставлен для продакшена.
        """
        # TODO: Интеграция с S3
        # import boto3
        # s3_client = boto3.client(
        #     's3',
        #     endpoint_url=settings.S3_ENDPOINT,
        #     aws_access_key_id=settings.S3_ACCESS_KEY,
        #     aws_secret_access_key=settings.S3_SECRET_KEY,
        #     region_name=settings.S3_REGION
        # )
        #
        # s3_client.upload_fileobj(
        #     file,
        #     settings.S3_BUCKET_NAME,
        #     filename,
        #     ExtraArgs={'ACL': 'public-read'}
        # )
        #
        # return f"{settings.S3_ENDPOINT}/{settings.S3_BUCKET_NAME}/{filename}"

        raise NotImplementedError("S3 integration not implemented yet")

    def delete_file(self, file_url: str) -> bool:
        """
        Удаление файла.

        Args:
            file_url: URL или путь к файлу

        Returns:
            True если удалён, False если нет
        """
        if self.use_s3:
            return self._delete_from_s3(file_url)
        else:
            return self._delete_locally(file_url)

    def _delete_locally(self, file_url: str) -> bool:
        """Удаление из локальной директории"""
        # file_url формата: /uploads/filename
        filename = file_url.split("/")[-1]
        file_path = os.path.join(self.upload_dir, filename)

        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
        except Exception:
            pass

        return False

    def _delete_from_s3(self, file_url: str) -> bool:
        """Удаление из S3"""
        # TODO: Интеграция с S3
        raise NotImplementedError("S3 integration not implemented yet")

    def optimize_image(self, file_path: str, max_width: int = 1920, max_height: int = 1080):
        """
        Оптимизация изображения (сжатие и ресайз).

        Args:
            file_path: Путь к файлу
            max_width: Макс. ширина
            max_height: Макс. высота

        Примечание: работает только для локального хранилища
        """
        if self.use_s3:
            return  # Для S3 оптимизацию можно делать через Lambda

        try:
            img = Image.open(file_path)

            # Конвертируем в RGB если RGBA
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')

            # Ресайз если больше макс. размера
            img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)

            # Сохраняем с оптимизацией
            img.save(file_path, optimize=True, quality=85)

        except Exception:
            pass  # Игнорируем ошибки оптимизации


# Singleton instance
media_service = MediaService()
