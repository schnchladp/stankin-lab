"""Собственные исключения проекта

Все ошибки приложения наследуются от DeliveryError, поэтому
их можно перехватить одним блоком ``except DeliveryError``.
"""


class DeliveryError(Exception):
    """Базовая ошибка службы доставки"""


class InvalidDataError(DeliveryError):
    """Переданы некорректные данные (пустое имя, плохой телефон и т.п.)"""


class NotFoundError(DeliveryError):
    """Объект с указанным id не найден"""


class DuplicateIdError(DeliveryError):
    """Объект с таким id уже существует"""


class DependencyError(DeliveryError):
    """Нельзя удалить или изменить объект: на него есть ссылки"""


class InvalidStatusError(DeliveryError):
    """Недопустимая смена статуса заказа или доставки"""


class CourierUnavailableError(DeliveryError):
    """Курьер сейчас занят и не может принять заказ"""


class StorageError(DeliveryError):
    """Ошибка чтения или записи файла JSON/XML"""
