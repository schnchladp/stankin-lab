# Лабораторная работа №2 - двоичные числа: проверка и поиск (вариант 26)

Программа проверяет, является ли строка двоичным числом, и ищет двоичные
числа в тексте: введённом пользователем, в файле и на веб-странице по URL.

## Формат двоичного числа

    <число>   ::= [<знак>] [<префикс>] <цифра> {<цифра>}
    <знак>    ::= "+" | "-"
    <префикс> ::= "0b" | "0B"
    <цифра>   ::= "0" | "1"

## Запуск

    python -m venv .venv && .venv\Scripts\activate    # Linux/macOS: source .venv/bin/activate
    pip install -r requirements.txt
    python main.py                                # меню (в PyCharm: Run для main.py)
    python main.py examples/input.txt             # файл -> examples/input_result.txt
    python main.py examples/input.txt -o out.txt  # файл -> out.txt

Команды выполняются из папки `lab2`.

Формат выходного файла: первая строка «Найдено: N», далее строки «число;десятичное значение».

## Тесты

    pytest                          # unit-тесты
    pytest --doctest-modules src    # примеры из docstring

## Структура

    main.py                         запуск программы
    src/binary_numbers/patterns.py  регулярные выражения
    src/binary_numbers/core.py      is_binary_number, find_binary_numbers, binary_to_int
    src/binary_numbers/sources.py   чтение файла, загрузка страницы (requests)
    src/binary_numbers/processing.py обработка: входной файл -> выходной файл
    src/binary_numbers/cli.py       консольное меню и параметры командной строки
    tests/                          pytest-тесты
    examples/                       input.txt, output.txt (пример результата), demo.html
    docs/                           отчёт (report_lab2.docx, report_lab2.pdf)

## Отчёт



[Открыть отчёт по лабораторной работе (PDF)](docs/report_lab2.pdf)

#

Сведения об авторе, группе, учебном заведении и дисциплине указаны в [главном README репозитория](../README.md).
