import struct
from pathlib import Path

import pytest

from machine import simulate
from translator import translate

PROJECT_ROOT = Path(__file__).parent.parent
PROGRAMS_DIR = PROJECT_ROOT / "programs"


@pytest.mark.golden_test("golden/*.yaml")
def test_programs(golden):
    # 1. Читаем параметры из эталона (yaml)
    source_name = golden["source_name"]
    input_str = golden.get("input", "")

    # Читаем исходный код программы
    asm_path = PROGRAMS_DIR / source_name
    source_code = asm_path.read_text(encoding="utf-8")

    # 2. Транслируем
    binary, debug, symbols = translate(source_code)

    # Формируем отладочный вывод (машинный код) для эталона
    debug_lines = []
    for addr, word, mnemon in debug:
        debug_lines.append(f"{addr:04X}  {word:08X}  {mnemon}")
    debug_out_str = "\n".join(debug_lines)

    # Собираем бинарник с заголовком entry_point
    assert "_start" in symbols, "В программе нет метки _start"
    entry_point = symbols["_start"]
    full_binary = struct.pack(">I", entry_point) + binary

    # 3. Симулируем (с запасом тактов)
    output, log = simulate(full_binary, input_str, max_ticks=200_000)

    # 4. Обрабатываем журнал
    # По ТЗ: "Если размер журнала слишком большой, его полное включение нецелесообразно.
    # Необходимо адаптировать журнал..."
    # Оставим первые 50 и последние 50 тактов.
    if len(log) > 120:
        short_log = "\n".join(
            log[:50] + ["\n... [ ЖУРНАЛ ОБРЕЗАН ] ...\n"] + log[-50:]
        )
    else:
        short_log = "\n".join(log)

    # 5. Проверяем данные с эталоном (поля out["..."] заполняются плагином)
    assert output == golden.out["expected_output"]
    assert debug_out_str == golden.out["expected_code"]
    assert short_log == golden.out["expected_log"]