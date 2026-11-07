# src/binary_numbers/cli.py
"""Консольный интерфейс: ввод пользователя, файл, веб-страница по URL"""

import argparse
from collections.abc import Callable, Sequence

import requests

from binary_numbers.core import (
    binary_to_int,
    find_binary_numbers,
    is_binary_number,
)
from binary_numbers.processing import process_file
from binary_numbers.sources import fetch_page_text, read_file

InputFn = Callable[[str], str]   # как input()
PrintFn = Callable[..., None]    # как print()

MENU = """\
=== Двоичные числа ===
1. Проверить, является ли строка двоичным числом
2. Найти двоичные числа в введённом тексте
3. Найти двоичные числа в файле
4. Найти двоичные числа на веб-странице (по URL)
5. Обработать файл: входной файл -> выходной файл
0. Выход"""


def format_matches(numbers: list[str]) -> str:
    """Формирует текст отчёта о найденных числах

    Examples:
        >>> print(format_matches(["101"]))
        Найдено двоичных чисел: 1
          1. 101  (в десятичной системе: 5)
        >>> format_matches([])
        'Двоичные числа не найдены.'
    """
    if not numbers:
        return "Двоичные числа не найдены."
    lines = [f"Найдено двоичных чисел: {len(numbers)}"]
    for index, number in enumerate(numbers, start=1):
        lines.append(
            f"  {index}. {number}  "
            f"(в десятичной системе: {binary_to_int(number)})"
        )
    return "\n".join(lines)


def _check_string(ask: InputFn, say: PrintFn) -> None:
    """Пункт 1: проверка введённой строки"""
    text = ask("Введите строку: ").strip()
    if is_binary_number(text):
        say(f"«{text}» — двоичное число "
            f"(десятичное значение: {binary_to_int(text)}).")
    else:
        say(f"«{text}» — НЕ двоичное число")


def _search_in_text(ask: InputFn, say: PrintFn) -> None:
    """Пункт 2: поиск в тексте, введённом пользователем"""
    text = ask("Введите текст: ")
    say(format_matches(find_binary_numbers(text)))


def _search_in_file(ask: InputFn, say: PrintFn) -> None:
    """Пункт 3: поиск в файле"""
    # кавычки убираем: Windows добавляет их при «копировать как путь»
    path = ask("Путь к файлу: ").strip().strip('"')
    try:
        text = read_file(path)
    except FileNotFoundError:
        say("Ошибка: файл не найден.")
    except UnicodeDecodeError:
        say("Ошибка: файл должен быть текстовым в кодировке UTF-8.")
    except OSError as err:  # нет прав, это каталог и т.п.
        say(f"Ошибка чтения файла: {err}")
    else:
        say(format_matches(find_binary_numbers(text)))


def _search_on_page(ask: InputFn, say: PrintFn) -> None:
    """Пункт 4: поиск на веб-странице по URL"""
    url = ask("Введите URL (http:// или https://): ").strip()
    try:
        text = fetch_page_text(url)
    except ValueError as err:
        say(f"Ошибка: {err}.")
    except requests.Timeout:
        say("Ошибка: сервер не ответил за отведённое время.")
    except requests.ConnectionError:
        say("Ошибка: не удалось соединиться с сервером.")
    except requests.RequestException as err:  # в том числе HTTP 404, 500
        say(f"Ошибка при загрузке страницы: {err}")
    else:
        say(format_matches(find_binary_numbers(text)))


def report_file_job(input_path: str, output_path: str | None, say: PrintFn
                    ) -> bool:
    """Обрабатывает файл и сообщает результат; True, если всё прошло успешно

    Общая часть пункта меню 5 и запуска из командной строки
    """
    try:
        target, numbers = process_file(input_path, output_path or None)
    except FileNotFoundError:
        say("Ошибка: входной файл не найден.")
    except UnicodeDecodeError:
        say("Ошибка: входной файл должен быть в кодировке UTF-8.")
    except ValueError as err:
        say(f"Ошибка: {err}.")
    except OSError as err:  # нет прав, каталог, нет папки для записи
        say(f"Ошибка работы с файлом: {err}")
    else:
        say(f"Найдено двоичных чисел: {len(numbers)}.")
        say(f"Результат записан в файл: {target}")
        return True
    return False


def _process_file_menu(ask: InputFn, say: PrintFn) -> None:
    """Пункт 5: входной файл -> выходной файл"""
    source = ask("Входной файл (имя или путь): ").strip().strip('"')
    target = ask("Выходной файл (Enter — результат запишется рядом с входным): ")
    target = target.strip().strip('"')
    report_file_job(source, target, say)


_ACTIONS = {
    "1": _check_string,
    "2": _search_in_text,
    "3": _search_in_file,
    "4": _search_on_page,
    "5": _process_file_menu,
}


def run_menu(input_fn: InputFn = input, print_fn: PrintFn = print) -> None:
    """Главный цикл меню

    Ввод и вывод передаются параметрами, чтобы меню можно было
    проверить unit-тестами без реальной клавиатуры и консоли
    """
    try:
        while True:
            print_fn(MENU)
            choice = input_fn("Выберите пункт: ").strip()
            if choice == "0":
                print_fn("До свидания!")
                return
            action = _ACTIONS.get(choice)
            if action is None:
                print_fn("Неверный пункт меню, введите число от 0 до 5.")
            else:
                action(input_fn, print_fn)
            print_fn()
    except (EOFError, KeyboardInterrupt):  # Ctrl+D / Ctrl+Z / Ctrl+C
        print_fn("\nЗавершение работы.")


def build_parser() -> argparse.ArgumentParser:
    """Параметры командной строки (без параметров запускается меню)"""
    parser = argparse.ArgumentParser(
        prog="binary_numbers",
        description="Поиск двоичных чисел: без параметров запускается меню, "
                    "с параметром input — обработка файла.",
    )
    parser.add_argument("input", nargs="?",
                        help="входной текстовый файл (UTF-8)")
    parser.add_argument("-o", "--output",
                        help="выходной файл (по умолчанию <имя>_result.txt)")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Точка входа программы

    Returns:
        Код завершения: 0 - успех, 1 - ошибка обработки файла
    """
    args = build_parser().parse_args(argv)
    if args.input is None:
        run_menu()
        return 0
    return 0 if report_file_job(args.input, args.output, print) else 1
