"""
Скрипт генерации секретных ключей для JWT.

Использование:
    python scripts/generate_keys.py
"""
import secrets
import string


def generate_secret_key(length: int = 64) -> str:
    """
    Генерация случайного секретного ключа.

    Args:
        length: Длина ключа

    Returns:
        Случайная строка
    """
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*()-_=+[]{}|;:,.<>?"
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def main():
    """Главная функция"""
    print("Генерация секретных ключей для JWT...\n")

    jwt_secret = generate_secret_key(64)

    print("Сгенерированные ключи:")
    print("=" * 80)
    print(f"\nJWT_SECRET_KEY={jwt_secret}")
    print("\n" + "=" * 80)

    print("\nДобавьте эти переменные в ваш .env файл:")
    print("\n# JWT Settings")
    print(f"JWT_SECRET_KEY={jwt_secret}")
    print("JWT_ALGORITHM=HS256")
    print("JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60")
    print("JWT_REFRESH_TOKEN_EXPIRE_DAYS=30")

    print("\n" + "=" * 80)
    print("\nВНИМАНИЕ: Сохраните эти ключи в безопасном месте!")
    print("Не публикуйте их в git или открытых источниках.")


if __name__ == "__main__":
    main()
