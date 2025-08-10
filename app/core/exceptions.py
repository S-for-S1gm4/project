"""
Кастомные исключения для Event Planner API
"""


class EventPlannerException(Exception):
    """Базовое исключение для приложения"""

    def __init__(self, message: str, error_code: str = None):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)


class UserNotFoundException(EventPlannerException):
    """Исключение когда пользователь не найден"""

    def __init__(self, user_identifier: str):
        message = f"User not found: {user_identifier}"
        super().__init__(message, "USER_NOT_FOUND")


class EventNotFoundException(EventPlannerException):
    """Исключение когда событие не найдено"""

    def __init__(self, event_id: int):
        message = f"Event not found: {event_id}"
        super().__init__(message, "EVENT_NOT_FOUND")


class InvalidCredentialsException(EventPlannerException):
    """Исключение при неверных учетных данных"""

    def __init__(self, message: str = "Invalid credentials"):
        super().__init__(message, "INVALID_CREDENTIALS")


class InsufficientBalanceException(EventPlannerException):
    """Исключение при недостаточном балансе"""

    def __init__(self, required_amount: float, current_balance: float):
        message = f"Insufficient balance. Required: {required_amount}, Available: {current_balance}"
        super().__init__(message, "INSUFFICIENT_BALANCE")


class EventFullException(EventPlannerException):
    """Исключение когда событие заполнено"""

    def __init__(self, event_title: str):
        message = f"Event '{event_title}' is full"
        super().__init__(message, "EVENT_FULL")


class EventNotActiveException(EventPlannerException):
    """Исключение когда событие неактивно"""

    def __init__(self, event_title: str, status: str):
        message = f"Event '{event_title}' is not active. Current status: {status}"
        super().__init__(message, "EVENT_NOT_ACTIVE")


class DuplicateUserException(EventPlannerException):
    """Исключение при попытке создать дубликат пользователя"""

    def __init__(self, email: str = None, username: str = None):
        if email and username:
            message = f"User with email '{email}' or username '{username}' already exists"
        elif email:
            message = f"User with email '{email}' already exists"
        elif username:
            message = f"User with username '{username}' already exists"
        else:
            message = "User already exists"
        super().__init__(message, "DUPLICATE_USER")


class ValidationException(EventPlannerException):
    """Исключение при ошибке валидации данных"""

    def __init__(self, field: str, message: str):
        full_message = f"Validation error for field '{field}': {message}"
        super().__init__(full_message, "VALIDATION_ERROR")


class PermissionDeniedException(EventPlannerException):
    """Исключение при недостаточных правах доступа"""

    def __init__(self, action: str, resource: str = None):
        if resource:
            message = f"Permission denied for action '{action}' on resource '{resource}'"
        else:
            message = f"Permission denied for action '{action}'"
        super().__init__(message, "PERMISSION_DENIED")


class BusinessLogicException(EventPlannerException):
    """Исключение при нарушении бизнес-логики"""

    def __init__(self, message: str):
        super().__init__(message, "BUSINESS_LOGIC_ERROR")


class ExternalServiceException(EventPlannerException):
    """Исключение при ошибке внешнего сервиса"""

    def __init__(self, service_name: str, message: str):
        full_message = f"External service '{service_name}' error: {message}"
        super().__init__(full_message, "EXTERNAL_SERVICE_ERROR")
