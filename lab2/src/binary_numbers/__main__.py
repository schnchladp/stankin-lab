# src/binary_numbers/__main__.py
"""Запуск: python -m binary_numbers [входной_файл [-o выходной_файл]]"""

import sys

from binary_numbers.cli import main

if __name__ == "__main__":
    sys.exit(main())
