"""Запуск программы: python main.py [входной_файл [-o выходной_файл]]"""

import sys
from pathlib import Path

# чтобы запуск работал из PyCharm и из консоли без настройки путей
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from binary_numbers.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
