# tests/test_cli.py
"""Тесты консольного меню: ввод и вывод подменяются списками"""

import runpy
from unittest.mock import MagicMock

import pytest
import requests

from binary_numbers import cli


def run(answers, monkeypatch=None):
    """Запускает меню с заранее заданными ответами, возвращает вывод"""
    it = iter(answers)
    out = []

    def fake_input(prompt=""):
        out.append(prompt)
        return next(it)

    cli.run_menu(fake_input, lambda *a: out.append(" ".join(map(str, a))))
    return "\n".join(out)


def test_exit():
    assert "До свидания" in run(["0"])


def test_unknown_item():
    assert "Неверный пункт" in run(["7", "0"])


def test_check_binary():
    out = run(["1", "0b101", "0"])
    assert "двоичное число" in out and "5" in out


def test_check_not_binary():
    assert "НЕ двоичное" in run(["1", "102", "0"])


def test_search_in_text():
    out = run(["2", "числа 101 и 11 и 12", "0"])
    assert "Найдено двоичных чисел: 2" in out
    assert "101" in out


def test_search_in_text_nothing():
    assert "не найдены" in run(["2", "ничего", "0"])


def test_file_ok(tmp_path):
    path = tmp_path / "f.txt"
    path.write_text("a 1010 b", encoding="utf-8")
    out = run(["3", f'"{path}"', "0"])        # путь в кавычках, как в Windows
    assert "1010" in out and "10" in out


def test_file_missing(tmp_path):
    assert "не найден" in run(["3", str(tmp_path / "x.txt"), "0"])


def test_file_bad_encoding(tmp_path):
    path = tmp_path / "b.txt"
    path.write_bytes("привет".encode("cp1251"))
    assert "UTF-8" in run(["3", str(path), "0"])


def test_file_is_directory(tmp_path):
    assert "Ошибка чтения файла" in run(["3", str(tmp_path), "0"])


def test_page_ok(monkeypatch):
    monkeypatch.setattr(cli, "fetch_page_text", lambda url: "код 101")
    out = run(["4", "https://a.ru", "0"])
    assert "Найдено двоичных чисел: 1" in out


def test_page_bad_url():
    assert "некорректный URL" in run(["4", "abc", "0"])


@pytest.mark.parametrize(
    "exc, message",
    [
        (requests.Timeout("t"), "не ответил"),
        (requests.ConnectionError("c"), "не удалось соединиться"),
        (requests.HTTPError("404 Not Found"), "404"),
    ],
)
def test_page_errors(monkeypatch, exc, message):
    monkeypatch.setattr(cli, "fetch_page_text", MagicMock(side_effect=exc))
    assert message in run(["4", "https://a.ru", "0"])


def test_eof_error(monkeypatch):
    def raise_eof(prompt=""):
        raise EOFError

    out = []
    cli.run_menu(raise_eof, lambda *a: out.append(" ".join(map(str, a))))
    assert any("Завершение" in line for line in out)


def test_keyboard_interrupt():
    def raise_ki(prompt=""):
        raise KeyboardInterrupt

    out = []
    cli.run_menu(raise_ki, lambda *a: out.append(" ".join(map(str, a))))
    assert any("Завершение" in line for line in out)


def test_format_matches():
    text = cli.format_matches(["101", "-0b1"])
    assert "101  (в десятичной системе: 5)" in text
    assert "-1" in text
    assert cli.format_matches([]) == "Двоичные числа не найдены."


def test_main_without_args_runs_menu(monkeypatch):
    called = MagicMock()
    monkeypatch.setattr(cli, "run_menu", called)
    assert cli.main([]) == 0
    called.assert_called_once_with()


def test_python_m_entry(monkeypatch):
    called = MagicMock(return_value=0)
    monkeypatch.setattr(cli, "main", called)
    with pytest.raises(SystemExit) as info:
        runpy.run_module("binary_numbers", run_name="__main__")
    assert info.value.code == 0
    called.assert_called_once()


# пункт 5 и запуск с параметрами: файл -> файл

def test_menu_file_to_file(tmp_path):
    src = tmp_path / "in.txt"
    src.write_text("a 101 b 12", encoding="utf-8")
    dst = tmp_path / "out.txt"
    out = run(["5", str(src), str(dst), "0"])
    assert "записан" in out
    assert dst.read_text(encoding="utf-8") == "Найдено: 1\n101;5\n"


def test_menu_file_to_file_default_name(tmp_path):
    src = tmp_path / "in.txt"
    src.write_text("11", encoding="utf-8")
    run(["5", str(src), "", "0"])
    assert (tmp_path / "in_result.txt").exists()


def test_menu_file_to_file_missing(tmp_path):
    out = run(["5", str(tmp_path / "x.txt"), "", "0"])
    assert "не найден" in out


def test_main_with_file(tmp_path, capsys):
    src = tmp_path / "in.txt"
    src.write_text("0b11 и 2", encoding="utf-8")
    dst = tmp_path / "res.txt"
    assert cli.main([str(src), "-o", str(dst)]) == 0
    assert "Найдено двоичных чисел: 1" in capsys.readouterr().out
    assert dst.read_text(encoding="utf-8") == "Найдено: 1\n0b11;3\n"


def test_main_with_missing_file_returns_1(tmp_path, capsys):
    assert cli.main([str(tmp_path / "none.txt")]) == 1
    assert "не найден" in capsys.readouterr().out


def test_report_file_job_errors(tmp_path):
    out = []
    say = lambda *a: out.append(" ".join(map(str, a)))
    bad = tmp_path / "cp.txt"
    bad.write_bytes("привет".encode("cp1251"))
    assert cli.report_file_job(str(bad), None, say) is False
    same = tmp_path / "same.txt"
    same.write_text("1", encoding="utf-8")
    assert cli.report_file_job(str(same), str(same), say) is False
    assert cli.report_file_job(
        str(same), str(tmp_path / "нет_папки" / "o.txt"), say) is False
    assert any("UTF-8" in m for m in out)
    assert any("не должен совпадать" in m for m in out)
    assert any("Ошибка работы с файлом" in m for m in out)
