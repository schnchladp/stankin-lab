# src/binary_numbers/core.py
"""Проверка, поиск и преобразование двоичных чисел"""

from binary_numbers.patterns import BINARY_FULL_RE, BINARY_SEARCH_RE


def is_binary_number(text: str) -> bool:
    """Проверяет, является ли строка целиком двоичным числом

    Args:
        text: строка для проверки

    Returns:
        True, если вся строка — двоичное число (с необязательными знаком
        и префиксом 0b/0B), иначе False. Для не-строк возвращает False

    Examples:
        >>> is_binary_number("101")
        True
        >>> is_binary_number("-0b1101")
        True
        >>> is_binary_number("102")
        False
    """
    if not isinstance(text, str):
        return False
    return BINARY_FULL_RE.match(text) is not None


def find_binary_numbers(text: str) -> list[str]:
    """Находит все двоичные числа в произвольном тексте

    Число считается найденным, только если оно отдельное «слово»:
    слева и справа нет букв, цифр и «_», а также это не часть
    десятичной дроби (3.101, 101.5)

    Args:
        text: текст, в котором ведётся поиск

    Returns:
        Список найденных чисел в порядке появления (как записаны в тексте)

    Raises:
        TypeError: если text не строка

    Examples:
        >>> find_binary_numbers("Числа 101, 0b11 и 102")
        ['101', '0b11']
        >>> find_binary_numbers("версия 1.0.1")
        []
    """
    if not isinstance(text, str):
        raise TypeError(
            f"text должен быть строкой, получено: {type(text).__name__}"
        )
    return BINARY_SEARCH_RE.findall(text)


def binary_to_int(number: str) -> int:
    """Переводит двоичное число (строку) в десятичное целое

    Args:
        number: строка, для которой is_binary_number(number) is True

    Returns:
        Значение числа в десятичной системе

    Raises:
        ValueError: если строка не является двоичным числом

    Examples:
        >>> binary_to_int("101")
        5
        >>> binary_to_int("-0b11")
        -3
    """
    match = BINARY_FULL_RE.match(number) if isinstance(number, str) else None
    if match is None:
        raise ValueError(f"не двоичное число: {number!r}")
    value = int(match["digits"], 2)
    return -value if match["sign"] == "-" else value
