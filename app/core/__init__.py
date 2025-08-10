
S-for-S1gm4/project
main

GITHUB

к этому решению комментарий преподавателя
Всё хорошо, но пожалуйста разнесите модели, бизнес логику и эндпоинты в разные файлы. Проект должен быть структурирован, для облегчения работы с ним и будущих изменений :)

помоги исправить

Давайте исправим структуру проекта согласно замечанию преподавателя. Основная проблема в том, что в файлах routes/ смешаны модели данных (Pydantic схемы), бизнес-логика и сами эндпоинты. Нужно их разделить.

Предлагаемая новая структура:
app/
├── main.py
├── requirements.txt
├── Dockerfile
├── database/
│   ├── __init__.py
│   ├── config.py
│   └── database.py
├── models/           # SQLModel модели (уже есть)
│   ├── __init__.py
│   ├── user.py
│   ├── event.py
│   └── transaction.py
├── schemas/          # NEW: Pydantic схемы для API
│   ├── __init__.py
│   ├── auth.py
│   ├── user.py
│   └── event.py
├── services/         # Бизнес-логика (уже есть)
│   ├── __init__.py
│   ├── user_service.py
│   └── event_service.py
├── routes/           # Только эндпоинты
│   ├── __init__.py
│   ├── auth.py
│   ├── user.py
│   └── events.py
├── core/             # NEW: Общие компоненты
│   ├── __init__.py
│   ├── auth.py       # Аутентификация
│   └── exceptions.py # Кастомные исключения
└── scripts/
    ├── __init__.py
    ├── init_demo_data.py
    └── test_system.py
Создадим новые файлы и перенесем код:


F

create_directory


Понял, мне нужно работать с уже загруженными файлами. Давайте создадим новую структуру на основе существующего кода.


schemas/__init__.py
Code

schemas/auth.py
Code

schemas/user.py
Code

schemas/event.py
Code
Теперь создадим модуль с общими компонентами аутентификации:


core/__init__.py
Code

core/auth.py
Code

core/exceptions.py
Code



Continue


core/exceptions.py
Code ∙ Version 2
Теперь создадим переработанные роуты без схем и бизнес-логики:


routes/auth.py (новая версия)
Code

routes/user.py (новая версия)
Code

routes/events.py (новая версия)
Code



Continue


routes/events.py (новая версия)
Code ∙ Version 2
Теперь обновим основной файл main.py для использования новой структуры:


main.py (обновленная версия)
Code
Теперь создадим обновленный README с описанием новой архитектуры:


README.md (обновленная версия)
Code



Continue


README.md (обновленная версия)
Code




"""
Core package - общие компоненты приложения
"""

from .auth import (
    create_jwt_token, hash_password, validate_password,
    verify_jwt_token, get_current_user, get_current_user_optional
)
from .exceptions import (
    EventPlannerException, UserNotFoundException, EventNotFoundException,
    InsufficientBalanceException, InvalidCredentialsException
)

__all__ = [
    # Auth utilities
    'create_jwt_token', 'hash_password', 'validate_password',
    'verify_jwt_token', 'get_current_user', 'get_current_user_optional',
    # Exceptions
    'EventPlannerException', 'UserNotFoundException', 'EventNotFoundException',
    'InsufficientBalanceException', 'InvalidCredentialsException'
]
