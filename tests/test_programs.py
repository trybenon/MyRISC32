"""Golden tests: транслируем .asm, запускаем симулятор, сверяем вывод."""
import struct
from pathlib import Path

from machine import simulate
from translator import translate

PROJECT_ROOT = Path(__file__).parent.parent
PROGRAMS_DIR = PROJECT_ROOT / "programs"


def build_and_run(asm_name: str, input_str: str = "", max_ticks: int = 100_000_000):
    """
    Хелпер: прочитать .asm, оттранслировать, запустить симулятор.
    Возвращает (output, log).
    """
    asm_path = PROGRAMS_DIR / asm_name
    source = asm_path.read_text(encoding="utf-8")

    binary, _debug, symbols = translate(source)

    # Собираем бинарник с заголовком entry_point
    assert "_start" in symbols, "В программе нет метки _start"
    entry_point = symbols["_start"]
    header = struct.pack(">I", entry_point)
    full_binary = header + binary

    return simulate(full_binary, input_str, max_ticks=max_ticks)


def test_hello():
    """hello.asm должна вывести 'Hello, World!\\n'."""
    output, _log = build_and_run("hello.asm")
    assert output == "Hello, World!\n"


def test_cat_passes_input():
    """cat.asm — каждый прочитанный символ выводит."""
    output, _log = build_and_run("cat.asm", input_str="gagarka")
    assert output == "gagarka"


def test_cat_empty_input():
    """cat без ввода: ничего не выводит, корректно завершается."""
    output, _log = build_and_run("cat.asm", input_str="")
    assert output == ""


def test_hello_user_name():
    """hello_user_name спрашивает имя и приветствует."""
    output, _log = build_and_run("hello_user_name.asm", input_str="Luke Skywalker\n")
    assert "What is your name?" in output
    assert "Luke Skywalker!" in output


def test_euler4():
    """Euler Problem 4: наибольший палиндром = 906609."""
    output, _log = build_and_run("euler4.asm")
    assert output.strip() == "906609"
