# src/binary_numbers/processing.py
"""Пакетная обработка: входной файл -> поиск чисел -> выходной файл"""

from pathlib import Path

from binary_numbers.core import binary_to_int, find_binary_numbers
from binary_numbers.sources import read_file

OUTPUT_ENCODING = "utf-8"


class OutputWriteError(OSError):
    """Не удалось записать выходной файл (чтобы отличать от ошибок чтения)"""


def default_output_path(input_path: str | Path) -> Path:
    """Имя выходного файла по умолчанию: рядом с входным, суффикс _result

    Examples:
        >>> default_output_path("data/sample.txt").as_posix()
        'data/sample_result.txt'
    """
    path = Path(input_path)
    return path.with_name(f"{path.stem}_result.txt")


def build_report(numbers: list[str]) -> str:
    """Формирует содержимое выходного файла

    Первая строка — количество найденных чисел, далее по строке на число
    в виде «число;десятичное значение» (удобно открыть в Excel)

    Examples:
        >>> build_report(["101", "-0b1"])
        'Найдено: 2\\n101;5\\n-0b1;-1\\n'
        >>> build_report([])
        'Найдено: 0\\n'
    """
    lines = [f"Найдено: {len(numbers)}"]
    lines += [f"{number};{binary_to_int(number)}" for number in numbers]
    return "\n".join(lines) + "\n"


def process_file(
    input_path: str | Path,
    output_path: str | Path | None = None,
) -> tuple[Path, list[str]]:
    """Читает входной файл, ищет двоичные числа и записывает результат

    Args:
        input_path: путь к входному текстовому файлу (UTF-8)
        output_path: путь к выходному файлу; если не задан, используется
            default_output_path(input_path)

    Returns:
        Пара (путь к созданному файлу, список найденных чисел)

    Raises:
        ValueError: выходной файл совпадает с входным
        FileNotFoundError, UnicodeDecodeError, OSError: ошибки чтения
            входного файла
        OutputWriteError: ошибка записи выходного файла
    """
    source = Path(input_path)
    target = Path(output_path) if output_path else default_output_path(source)
    if target.resolve() == source.resolve():
        raise ValueError("выходной файл не должен совпадать с входным")

    numbers = find_binary_numbers(read_file(source))
    try:
        target.write_text(build_report(numbers), encoding=OUTPUT_ENCODING)
    except OSError as err:
        raise OutputWriteError(
            f"не удалось записать файл {target}: {err}") from err
    return target, numbers
