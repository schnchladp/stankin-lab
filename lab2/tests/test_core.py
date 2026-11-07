# tests/test_core.py
"""Тесты проверки, поиска и перевода двоичных чисел"""

import pytest

from binary_numbers import binary_to_int, find_binary_numbers, is_binary_number
from binary_numbers.patterns import BINARY_FULL_RE


# ---------- is_binary_number

def test_valid_numbers(valid_numbers):
    for number in valid_numbers:
        assert is_binary_number(number), f"должно быть числом: {number!r}"


def test_invalid_numbers(invalid_numbers):
    for number in invalid_numbers:
        assert not is_binary_number(number), f"не должно быть: {number!r}"


@pytest.mark.parametrize("value", [None, 101, 1.0, b"101", ["1"], True])
def test_non_string_is_not_binary(value):
    assert is_binary_number(value) is False


def test_named_groups():
    match = BINARY_FULL_RE.match("-0b1101")
    assert match["sign"] == "-"
    assert match["prefix"] == "0b"
    assert match["digits"] == "1101"


def test_named_groups_optional_parts_absent():
    match = BINARY_FULL_RE.match("101")
    assert match["sign"] is None
    assert match["prefix"] is None
    assert match["digits"] == "101"


# find_binary_numbers

@pytest.mark.parametrize(
    "text, expected",
    [
        ("101", ["101"]),
        ("Числа 101, 0b11 и 102", ["101", "0b11"]),
        ("a 1 b 0 c", ["1", "0"]),
        ("-101 и +0B11", ["-101", "+0B11"]),
        ("(101) [10] {11}", ["101", "10", "11"]),
        ("101, 110; 111.", ["101", "110", "111"]),   # точка в конце фразы
        ("1\n0\t1", ["1", "0", "1"]),
        ("0010", ["0010"]),
    ],
)
def test_find_positive(text, expected):
    assert find_binary_numbers(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "",
        "нет чисел",
        "102 2024 9",
        "12ab ab12 a101 101b",       # приклеено к буквам
        "x_101 101_x 1_000",         # подчёркивание
        "3.101 101.5 3,101 101,5",   # десятичные дроби
        "версия 1.0.1",
        "01.01.2025",
        "0x1F 0b",
        "1012 21",
    ],
)
def test_find_negative(text):
    assert find_binary_numbers(text) == []


def test_find_returns_list_in_order():
    assert find_binary_numbers("11 00 10") == ["11", "00", "10"]


@pytest.mark.parametrize("value", [None, 101, b"101", ["101"]])
def test_find_rejects_non_string(value):
    with pytest.raises(TypeError):
        find_binary_numbers(value)


# binary_to_int

@pytest.mark.parametrize(
    "number, expected",
    [
        ("0", 0), ("1", 1), ("101", 5), ("0010", 2),
        ("+101", 5), ("-101", -5), ("-0", 0),
        ("0b1101", 13), ("0B1101", 13), ("-0b11", -3),
        ("1" * 64, 2 ** 64 - 1),
    ],
)
def test_binary_to_int(number, expected):
    assert binary_to_int(number) == expected


@pytest.mark.parametrize("value", ["", "102", "0b", "1 0", "101\n", None, 5])
def test_binary_to_int_errors(value):
    with pytest.raises(ValueError):
        binary_to_int(value)


def test_roundtrip_with_python_int():
    for n in range(-40, 40):
        text = bin(n)           # '-0b101' и т.п.
        assert is_binary_number(text)
        assert binary_to_int(text) == n
