"""
Скрипт инициализации базы данных.

Создаёт все таблицы и опционально создаёт первого администратора.

Использование:
    python scripts/init_db.py
"""
import sys
import os

# Добавляем корневую директорию в PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database import init_db, SessionLocal
from app.models import User, UserRole


def create_admin_user(phone: str = "+79991111111", full_name: str = "Administrator"):
    """
    Создание первого администратора.

    Args:
        phone: Номер телефона администратора
        full_name: Имя администратора
    """
    db = SessionLocal()

    try:
        # Проверяем существует ли уже администратор
        existing_admin = db.query(User).filter(
            User.role == UserRole.ADMIN
        ).first()

        if existing_admin:
            print(f"Администратор уже существует: {existing_admin.phone}")
            return

        # Создаём администратора
        admin = User(
            phone=phone,
            full_name=full_name,
            role=UserRole.ADMIN,
            is_active=True
        )

        db.add(admin)
        db.commit()
        db.refresh(admin)

        print(f"Администратор создан успешно:")
        print(f"  ID: {admin.id}")
        print(f"  Phone: {admin.phone}")
        print(f"  Name: {admin.full_name}")
        print(f"\nДля входа запросите OTP на номер {admin.phone}")

    except Exception as e:
        print(f"Ошибка создания администратора: {str(e)}")
        db.rollback()

    finally:
        db.close()


def main():
    """Главная функция"""
    print("Инициализация базы данных...")

    # Создание таблиц
    init_db()
    print("Таблицы созданы успешно")

    # Создание администратора
    print("\nСоздание первого администратора...")
    create_choice = input("Создать администратора? (y/n): ").lower()

    if create_choice == 'y':
        phone = input("Номер телефона (+79991234567): ").strip() or "+79991111111"
        name = input("Имя (Administrator): ").strip() or "Administrator"

        create_admin_user(phone, name)
    else:
        print("Администратор не создан")

    print("\nИнициализация завершена!")


if __name__ == "__main__":
    main()
