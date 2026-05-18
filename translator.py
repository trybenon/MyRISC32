import sys
import struct
from isa import OPCODES, FUNCT, REGISTERS, R_TYPE, I_TYPE, J_TYPE, PSEUDO

def clean_lines(sourse: str) -> list[tuple[int, str]]:
    result: list[tuple[int, str]] = []

    for lineno, line in enumerate(sourse.splitlines(), start=1):
        line = line.split(";")[0].strip()
        if line:
            result.append((lineno, line))

    return result

def tokenize(line: str) -> list[str]:

    line = line.replace(",", " ").replace("(", " ").replace(")", " ")

    return  line.split()

def parse_string(line: str) -> str:

     start = line.index('"') + 1
     end = line.rindex('"')
     raw = line[start:end]

     return raw.encode("raw_unicode_escape").decode("unicode_escape")

def first_pass(lines: list[tuple[int, str]]) -> dict[str, int]:
    symbols: dict[str, int] = {}

    pc: int = 0

    for lineno, line in lines:
        tokens = tokenize(line)


        if tokens[0] == ".data" or tokens[0] == ".text":
            continue

        # .org: переставить счётчик адресов вперёд
        if tokens[0] == ".org":
            target = int(tokens[1], 0)
            if target < pc:
                raise ValueError(
                    f"Строка {lineno}: .org {target:#x} меньше "
                    f"текущего адреса {pc:#x} — нельзя идти назад"
                )
            pc = target
            continue

        if tokens[0].endswith(":"):
            label_name = tokens[0][:-1]
            symbols[label_name] = pc

            # После метки может быть инструкция на той же строке:
            tokens = tokens[1:]
            if not tokens:  # если после метки ничего нет — следующая строка
                continue

        if tokens[0] == ".word":
            pc += 4  # одно слово = 4 байта
            continue

        if tokens[0] == ".cstr":
            s = parse_string(line)
            # Каждый символ = 1 слово (4 байта) + нулевой терминатор
            pc += (len(s) + 1) * 4
            continue

        # раскрываются в 2 инструкции
        if tokens[0] in ("li", "la"):
            pc += 8
            continue

        # обычная инструкция = 4 байта
        if tokens[0] in OPCODES or tokens[0] in PSEUDO:
            pc += 4

    return symbols

def encode_r(opcode: int, rd:int, rs1: int, rs2: int, func: int) -> bytes:
    """
        Упаковывает R-type инструкцию в 4 байта.
        Формат: [opcode 7][rd 3][rs1 3][rs2 3][funct 16] = 32 бита
    """
    word: int =(
    (opcode << 25) |
    (rd << 22) |
    (rs1 << 19) |
    (rs2 << 16) |
    func
    )

    return struct.pack(">I", word)

def encode_i(opcode: int, rd: int, rs1: int, imm: int) -> bytes:
    """
    Упаковывает I-type инструкцию в 4 байта.
    Формат: [opcode 7][rd 3][rs1 3][imm 19] = 32 бита
    """
    # & 0x7FFFF — оставить только младшие 19 бит.
    # Если imm = -1 (0xFFFFFFFF...), то -1 & 0x7FFFF = 0x7FFFF.
    imm = imm & 0x7FFFF

    word: int = (
        (opcode << 25) |
        (rd << 22) |
        (rs1 << 19) |
        imm
    )
    return struct.pack(">I", word)


def encode_j(opcode: int, addr: int) -> bytes:
    """
    Упаковывает J-type инструкцию в 4 байта.
    Формат: [opcode 7][addr 25] = 32 бита
    """
    addr = addr & 0x1FFFFFF  # 25 бит
    word: int = (opcode << 25) | addr
    return struct.pack(">I", word)

def reg(name: str) -> int:
    """
        Имя регистра → номер (0..7).
        Бросает понятную ошибку если регистр не найден.
    """
    name = name.strip()
    if name not in REGISTERS:
        raise ValueError(f"Неизвестный регистр: {name!r}")
    return REGISTERS[name]

def resolve(token: str, symbols: dict[str, int], pc: int) -> int:
    """
        Превращает токен в числовое значение.
        Понимает:
          - числа: "42", "0xFF", "-1"
          - метки: "loop", "_start"
          - %hi(sym): верхние 20 бит адреса символа
          - %lo(sym): нижние 12 бит адреса символа
    """
    token = token.strip()

    if token.startswith("%hi("):
        sym = token[4:-1]
        return (symbols[sym] >> 12) & 0xFFFFF

    if token.startswith("%lo("):
        sym = token[4:-1]
        return symbols[sym] & 0xFFF

    if token in symbols:
        return symbols[token]

    return int(token, 0)

def encode_instruction(mnemonic: str, args: list[str], symbols: dict[str, int], pc: int) -> bytes:
    """
      Кодирует одну инструкцию в 4 байта.

      mnemonic — название инструкции ("add", "lw", ...)
      args     — список аргументов после мнемоники
      symbols  — таблица символов из первого прохода
      pc       — текущий адрес (нужен для вычисления relative-переходов)
      """
    op: int = OPCODES[mnemonic]

    # R-type арифметика: add rd, rs1, rs2
    if mnemonic in FUNCT:
        rd = reg(args[0])
        rs1 = reg(args[1])
        rs2 = reg(args[2])
        return encode_r(op, rd, rs1, rs2, FUNCT[mnemonic])

    # R-type ветвления: beq rs1, rs2, label
    # funct - смещение перехода(знаковое, в словах)
    if mnemonic in {"beq", "bne", "bgt", "ble"}:
        rs1 = reg(args[0])
        rs2 = reg(args[1])
        target = resolve(args[2], symbols, pc)
        offset = (target - pc) // 4
        return encode_r(op, 0, rs1, rs2, offset & 0xFFFF)

    # J-type: j label
    if mnemonic == "j":
        target = resolve(args[0], symbols, pc)
        offset = (target - pc) // 4
        return encode_j(op, offset)

    # lui rd, imm
    if mnemonic == "lui":
        rd = reg(args[0])
        imm = resolve(args[1], symbols, pc)
        return encode_i(op, rd, 0, imm)

    # lw rd, imm(rs1)
    if mnemonic == "lw":
        rd = reg(args[0])
        # tokenize: "lw t0, 4(sp)" -> ["lw", "t0", "4", "sp"]
        # args = ["t0", "4", "sp"]
        imm = resolve(args[1], symbols, pc)
        rs1 = reg(args[2])
        return encode_i(op, rd, rs1, imm)

    # sw rd, imm(rs1)
    if mnemonic == "sw":
        rd = reg(args[0])
        imm = resolve(args[1], symbols, pc)
        rs1 = reg(args[2])
        return encode_i(op, rd, rs1, imm)

    # beqz/bnez rs1, label
    if mnemonic in {"beqz", "bnez"}:
        rs1 = reg(args[0])
        target = resolve(args[1], symbols, pc)
        offset = (target - pc) // 4
        return encode_i(op, 0, rs1, offset)

    # jal label (call)
    # Сохраняет PC+4 в ra, прыгает на метку
    if mnemonic == "jal":
        target = resolve(args[0], symbols, pc)
        offset = (target - pc) // 4
        return encode_i(op, reg("ra"), 0, offset)

    # jr rs1 (return)
    if mnemonic == "jr":
        return encode_i(op, 0, reg(args[0]), 0)

    # mv rd, rs1
    if mnemonic == "mv":
        rd = reg(args[0])
        rs1 = reg(args[1])
        return encode_i(op, rd, rs1, 0)

    # halt
    if mnemonic == "halt":
        return encode_i(0x00, 0,0,0)

    # Общий случай I-type: mnemonic rd, rs1, imm
    # addi, andi, ori, xori, slli, srli, slti
    rd = reg(args[0])
    rs1 = reg(args[1])
    imm = resolve(args[2], symbols, pc)
    return encode_i(op, rd, rs1, imm)

def second_pass(lines: list[tuple[int, str]],
                symbols: dict[str, int],
                ) -> tuple[bytes, list[tuple[int, int, str]]]:
    """
       Второй проход: генерируем бинарный код.

       Возвращает кортеж из двух элементов:
         1. bytes — готовый бинарник
         2. list[tuple[int, int, str]] — отладочный дамп:
            каждый элемент = (адрес, слово, мнемоника)
       """
    binary: bytearray = bytearray()

    debug: list[tuple[int, int, str]] = []
    pc: int = 0
    for lineno, line in lines:
        tokens = tokenize(line)
        if tokens[0] in {".data", ".text"}:
            continue
        # .org: заполнить промежуток нулями и переставить счётчик
        if tokens[0] == ".org":
            target = int(tokens[1], 0)
            if target < pc:
                 raise ValueError(
                    f"Строка {lineno}: .org {target:#x} меньше "
                    f"текущего адреса {pc:#x} — нельзя идти назад"
                )
            # Заполняем нулями чтобы len(binary) == target
            # Без этого адреса всех следующих инструкций съедут
            binary += b"\x00" * (target - pc)
            pc = target
            continue
