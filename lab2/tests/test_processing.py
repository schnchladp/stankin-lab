# tests/test_processing.py
"""Тесты обработки «входной файл -> выходной файл»"""

import pytest

from binary_numbers.processing import (
    build_report,
    default_output_path,
    OutputWriteError,
    process_file,
)


def test_default_output_path(tmp_path):
    assert default_output_path(tmp_path / "a.txt") == tmp_path / "a_result.txt"


def test_default_output_path_no_extension(tmp_path):
    assert default_output_path(tmp_path / "data").name == "data_result.txt"


def test_build_report():
    assert build_report(["101", "-0b11", "0010"]) == (
        "Найдено: 3\n101;5\n-0b11;-3\n0010;2\n"
    )


def test_build_report_empty():
    assert build_report([]) == "Найдено: 0\n"


def test_process_file_explicit_output(tmp_path):
    src = tmp_path / "in.txt"
    src.write_text("Числа: 101, 0b11, 102, 3.101", encoding="utf-8")
    dst = tmp_path / "out.txt"
    path, numbers = process_file(src, dst)
    assert path == dst
    assert numbers == ["101", "0b11"]
    assert dst.read_text(encoding="utf-8") == "Найдено: 2\n101;5\n0b11;3\n"


def test_process_file_default_output(tmp_path):
    src = tmp_path / "in.txt"
    src.write_text("1 0", encoding="utf-8")
    path, numbers = process_file(src)
    assert path == tmp_path / "in_result.txt"
    assert numbers == ["1", "0"]
    assert path.exists()


def test_process_file_no_numbers_still_creates_file(tmp_path):
    src = tmp_path / "in.txt"
    src.write_text("ничего", encoding="utf-8")
    path, numbers = process_file(src)
    assert numbers == []
    assert path.read_text(encoding="utf-8") == "Найдено: 0\n"


def test_process_file_overwrites_existing_output(tmp_path):
    src = tmp_path / "in.txt"
    src.write_text("1", encoding="utf-8")
    dst = tmp_path / "out.txt"
    dst.write_text("старое содержимое", encoding="utf-8")
    process_file(src, dst)
    assert dst.read_text(encoding="utf-8") == "Найдено: 1\n1;1\n"


def test_process_file_reads_bom(tmp_path):
    src = tmp_path / "bom.txt"
    src.write_bytes("﻿101".encode("utf-8"))
    assert process_file(src)[1] == ["101"]


def test_process_file_same_input_and_output(tmp_path):
    src = tmp_path / "in.txt"
    src.write_text("101", encoding="utf-8")
    with pytest.raises(ValueError):
        process_file(src, src)
    assert src.read_text(encoding="utf-8") == "101"   # файл не испорчен


def test_process_file_missing_input(tmp_path):
    with pytest.raises(FileNotFoundError):
        process_file(tmp_path / "none.txt")


def test_process_file_wrong_encoding(tmp_path):
    src = tmp_path / "cp.txt"
    src.write_bytes("привет".encode("cp1251"))
    with pytest.raises(UnicodeDecodeError):
        process_file(src)


def test_process_file_unwritable_output(tmp_path):
    src = tmp_path / "in.txt"
    src.write_text("1", encoding="utf-8")
    with pytest.raises(OutputWriteError):
        process_file(src, tmp_path / "нет_папки" / "out.txt")
