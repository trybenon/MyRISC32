import opcode
import struct
from dataclasses import dataclass

from isa import IO_IN, IO_OUT

# =================================================================
# MEMORY
# =================================================================
class Memory:

    def __init__(self, size: int, input_tokens: list[int]):
        # Память(размер в словах)
        self._data: list[int] = [0] * (size // 4)
        # Входной поток
        self._input: list[int] = input_tokens
        # Выходной поток
        self._output: list[int] = []

    def load(self, binary: bytes):
        """
        Загружает бинарник в память начиная с адреса 0.
        """
        entry_point = struct.unpack_from(">I", binary, 0)[0]
        code = binary[4:]
        for byte_addr in range(0, len(code), 4):
            word = struct.unpack_from(">I", code, byte_addr)[0]
            self._data[byte_addr // 4] = word
        return entry_point

    def read(self, byte_addr: int) -> int:
        """
        Читает одно машинное слово по байтовому адресу.
        Если адрес == 0x80 — читает из входного потока.
        """
        if byte_addr == IO_IN:
            if not self._input:
                raise StopIteration("Входной буфер пуст - EOF")
            return self._input.pop(0)

        idx = byte_addr // 4
        if idx < 0 or idx >= len(self._data):
            raise IndexError(f"Адрес вне памяти: {byte_addr:#x}")
        return self._data[idx]

    def write(self, byte_addr: int, value: int) -> None:
        """
        Записывает одно машинное слово по байтовому адресу.
        Если адрес == 0x84 — пишет в выходной поток.
        """
        if byte_addr == IO_OUT:
            self._output.append(value & 0xFF)
            return

        idx = byte_addr // 4
        if idx < 0 or idx >= len(self._data):
            raise IndexError(f"Адрес вне памяти: {byte_addr:#x}")
        self._data[idx] = value & 0xFFFFFFFF

    def get_output(self) -> str:
        """Возвращает выходной буфер как строку."""
        return "".join(chr(c) for c in self._output)


# =================================================================
# REGISTER FILE
# =================================================================

class RegisterFile:
    """
    Банк из 8 регистров общего назначения.
    r0 (zero) всегда равен 0 — запись игнорируется.
    """

    def __init__(self):
        self._regs: list[int] = [0] * 8

    def read(self, reg_num: int) -> int:
        """Прочитать значение по регистру"""
        if reg_num < 0 or reg_num > 7:
            raise ValueError(f"Неверный номер регистра: {reg_num}")
        return self._regs[reg_num]

    def write(self, reg_num: int, value: int) -> None:
        """
        Записать значение в регистр.
        Если reg_num == 0 — игнорируем.
        """
        if reg_num < 0 or reg_num > 7:
            raise ValueError(f"Неверный номер регистра: {reg_num}")

        if reg_num == 0:
            return

        # Обрезаем до знакового 32-битного числа.
        value = value & 0xFFFFFFFF
        if value >= 0x80000000:
            value -= 0x100000000
        self._regs[reg_num] = value

    def dump(self) -> str:
        """
        Возвращает строку с состоянием всех регистров.
        Используется в логе на каждом такте.

        Пример вывода:
        zero=0 ra=0 sp=0 t0=128 t1=132 a0=72 a1=0 a2=0
        """
        names = ["zero", "ra", "sp", "t0", "t1", "a0", "a1", "a2"]
        parts = [
            f"{name}={self._regs[i]}"
            for i, name in enumerate(names)
        ]

        return " ".join(parts)

# =================================================================
# ALU
# =================================================================

class ALU:
    """
    Арифметико-логическое устройство.
    Принимает два операнда и код операции, возвращает результат.
    """

    def compute(self, op: str, a: int, b: int) -> int:
        """
        op — строка-название операции: "add", "sub", "mul" и т.д.
        a, b — знаковые 32-битные операнды.
        Возвращает знаковый 32-битный результат.
        """
        match op:
            case "add":
                result = a + b

            case "sub":
                result = a - b

            case "mul":
                result = a * b

            case "div":
                # Деление на 0 — возвращаем -1.
                result = -1 if b == 0 else int(a / b)

            case "rem":
                # Остаток от деления. Если b == 0 — возвращаем a.
                result = a if b == 0 else a % b

            case "and":
                result = a & b

            case "or":
                result = a | b

            case "xor":
                result = a ^ b

            case "sll":
                # Сдвиг влево
                result = a << (b & 0x1F)

            case "srl":
                # Логический сдвиг вправо
                result = (a & 0xFFFFFFFF) >> (b & 0x1F)

            case "slt":
                # Set Less Than: если a < b — возвращаем 1, иначе 0
                # Используется в slti инструкции
                result = 1 if a < b else 0

            case "passa":
                # "pass a" — просто вернуть a без изменений
                # Нужно для mv и lui
                result = a

            case _:
                # ничего не совпало
                raise ValueError(f"Неизвестная операция ALU: {op!r}")

        # Обрезаем результат до знакового 32-битного числа.
        result = result & 0xFFFFFFFF
        if result >= 0x80000000:
            result -= 0x100000000
        return result

# =================================================================
# DataPath
# =================================================================
class DataPath:
    """Содержит все компоненты процессора и внутренние регистры (PC, IR, AR, MDR)
     Выполняет управляющие сигналы одного такта."""
    def __init__(self, memory: Memory, start_pc: int ):
        self.memory: Memory = memory
        self.regs = RegisterFile()
        self.alu = ALU()

        # Внутренние регистры
        self.pc: int = start_pc
        self.ir: int = 0
        self.ar: int = 0
        self.mdr: int = 0

    #Декодирование полей инструкции
    @property
    def ir_opcode(self) -> int:
        """Биты 31:25 - оп-код (7 бит)"""
        return (self.ir >> 25) & 0x7F
    @property
    def ir_rd(self) -> int:
        """Биты 24:22 - регистр назначения (3 бита)"""
        return (self.ir >> 22) & 0x7
    @property
    def ir_rs1(self) -> int:
        """Биты 21:19 - первый регистр источник (3 бита)"""
        return (self.ir >> 19) & 0x7
    @property
    def ir_rs2(self) -> int:
        """Биты 18:16 - второй регистр-источник (3 бита, только R-type)."""
        return (self.ir >> 16) & 0x7
    @property
    def ir_imm(self) -> int:
        """
        Биты 18:0 - непосредственное значение I-type (19 бит),
        знаково расширенное до 32 бит.
        """
        raw = self.ir & 0x7FFFF
        if raw & 0x40000:
            raw -= 0x80000
        return raw
    @property
    def ir_imm_u(self) -> int:
        """
        Биты 21:0 - непосредственное значение U-type (22 бита),
        для инструкции lui. Знаково расширяем до 32 бит.
        """
        raw = self.ir & 0x3FFFFF
        if raw & 0x200000:
            raw -= 0x400000
        return raw

    @property
    def ir_funct(self) -> int:
        """
        Биты 15:0 — поле funct (16 бит), знаково расширенное.
        Для R-type ветвлений здесь смещение перехода.
        """
        raw = self.ir & 0xFFFF
        if raw & 0x8000:
            raw -= 0x10000
        return raw

    @property
    def ir_jaddr(self) -> int:
        """
        Биты 24:0 — адрес перехода J-type (25 бит), знаково расширен.
        Только для инструкции j.
        """
        raw = self.ir & 0x1FFFFFF
        if raw & 0x1000000:
            raw -= 0x2000000
        return raw


    # СИГНАЛЫ — действия одного такта

    def signal_fetch(self) -> None:
        """Первый такт всех инструкций."""
        self.ir = self.memory.read(self.pc)
        self.pc += 4

    def signal_calc_addr(self) -> None:
        """
        Вычисление адреса для lw/sw:
            AR ← regs[rs1] + imm
        """
        rs1_val = self.regs.read(self.ir_rs1)
        self.ar = self.alu.compute("add", rs1_val, self.ir_imm)

    def signal_mem_read(self) -> None:
        """
        Чтение из памяти:
            MDR ← MEM[AR]
        """
        self.mdr = self.memory.read(self.ar)

    def signal_mem_write(self) -> None:
        """
        Запись в память:
            MEM[AR] ← regs[rd]
        """
        self.memory.write(self.ar, self.regs.read(self.ir_rd))

    def signal_writeback(self) -> None:
        """
        Запись прочитанного в регистр:
            regs[rd] ← MDR
        Используется после signal_mem_read для lw.
        """
        self.regs.write(self.ir_rd, self.mdr)

    def signal_alu_r(self, op: str) -> None:
        """
        R-type арифметика:
            regs[rd] ← ALU(regs[rs1], regs[rs2])
        """
        a = self.regs.read(self.ir_rs1)
        b = self.regs.read(self.ir_rs2)
        self.regs.write(self.ir_rd, self.alu.compute(op, a, b))

    def signal_alu_i(self, op: str) -> None:
        """
        I-type арифметика:
            regs[rd] ← ALU(regs[rs1], imm)
        """
        a = self.regs.read(self.ir_rs1)
        self.regs.write(self.ir_rd, self.alu.compute(op, a, self.ir_imm))

    def signal_lui(self) -> None:
        """
        lui rd, imm:
            regs[rd] ← (imm & 0xFFFFF) << 12
        Берём 20 бит из 22-битного U-type поля, сдвигаем в верх.
        """
        self.regs.write(self.ir_rd, (self.ir_imm_u & 0xFFFFF) << 12)

    def signal_mv(self) -> None:
        """
        mv rd, rs1:
            regs[rd] ← regs[rs1]
        """
        self.regs.write(self.ir_rd, self.regs.read(self.ir_rs1))

    # --- Ветвления и переходы ---
    # К моменту вызова signal_fetch уже увеличил PC на 4.
    # Смещение отсчитывается от адреса самой инструкции,
    # поэтому откатываемся: (PC - 4) + offset * 4.

    def signal_branch_i(self, taken: bool) -> None:
        """
        I-type ветвление (beqz/bnez):
            если taken: PC ← (PC - 4) + imm * 4
        """
        if taken:
            self.pc = (self.pc - 4) + self.ir_imm * 4

    def signal_branch_r(self, taken: bool) -> None:
        """
        R-type ветвление (beq/bne/bgt/ble):
            если taken: PC ← (PC - 4) + funct * 4
        """
        if taken:
            self.pc = (self.pc - 4) + self.ir_funct * 4

    def signal_jump(self) -> None:
        """
        j label:
            PC ← (PC - 4) + jaddr * 4
        """
        self.pc = (self.pc - 4) + self.ir_jaddr * 4

    def signal_jal(self) -> None:
        """
        jal label:
            regs[ra] ← PC
            PC ← (PC - 4) + imm * 4
        ra = регистр 1.
        """
        self.regs.write(1, self.pc)
        self.pc = (self.pc - 4) + self.ir_imm * 4

    def signal_jr(self) -> None:
        """
        jr rs1:
            PC ← regs[rs1]
        """
        self.pc = self.regs.read(self.ir_rs1)


    # ОТЛАДКА
    def dump(self) -> str:
        """Строка состояния процессора для лога."""
        return (
            f"PC={self.pc:#06x} "
            f"IR={self.ir:#010x} "
            f"AR={self.ar:#06x} "
            f"| {self.regs.dump()}"
        )

# =================================================================
# MICROINSTRUCTION
# =================================================================

@dataclass
class MicroInstruction:
    """
    Одна микроинструкция = один такт = набор управляющих сигналов.

    action — название метода DataPath который надо вызвать,
            или None если на этом такте действие не нужно.
    arg   — аргумент для метода (например "add" для signal_alu_r).
    next_mpc — что делать с mPC после этого такта:
            "+1"     — следующая микроинструкция
            "decode" — прыгнуть по декодеру (после fetch)
            "reset"  — вернуться к fetch (mPC = 0)
    """
    action: str | None = None
    arg: str | None = None
    next_mpc: str = "+1"
    comment: str = "" # для лога

# =================================================================
# MICROCODE — таблица микропрограмм
# =================================================================

MICROCODE: dict[int, MicroInstruction] = {

    # FETCH + DECODE (общие для всех инструкций)
    0:MicroInstruction(action="signal_fetch",
                       next_mpc="decode",
                       comment="FETCH: IR=MEM[PC], PC+=4"
                       ),
    # add/sub/mul/... (R-type арифметика)
    10:MicroInstruction(action="signal_alu_r",
                        arg=None, # операция определяется по funct
                        next_mpc="reset",
                        comment="R-type: rd = rs1 OP rs2"
                        ),
    11:MicroInstruction(action="signal_alu_i",
                        arg=None,
                        next_mpc="reset",
                        comment="R-type: rd = rs1 OP imm"),

    # lui
    12: MicroInstruction(action="signal_lui",
                         next_mpc="reset",
                         comment="lui: rd = imm << 12",
    ),

    # lw
    20: MicroInstruction(action="signal_calc_addr",
                         next_mpc="+1",
                         comment="lw: AR = rs1 + imm",
    ),
    21: MicroInstruction(action="signal_mem_read",
                         next_mpc="+1",
                         comment="lw: MDR = MEM[AR]",
    ),
    22: MicroInstruction(action="signal_writeback",
                         next_mpc="reset",
                         comment="lw: rd = MDR",
    ),
    # sw
    30: MicroInstruction(action="signal_calc_addr",
                         next_mpc="+1",
                         comment="sw: AR = rs1 + imm",
    ),
    31: MicroInstruction(action="signal_mem_write",
                         next_mpc="reset",
                         comment="sw: MEM[AR] = rd",
    ),

    # mv
    40: MicroInstruction(action="signal_mv",
                         next_mpc="reset",
                         comment="mv: rd = rs1",
    ),

    # Ветвления I-type(beqz/bnez)
    # Условие вычисляет Control Unit и передает через arg
    50: MicroInstruction(action="signal_branch_i",
                         arg=None,
                         next_mpc="reset",
                         comment="beqz/bnez: if cond PC += imm"),

    # Ветвления R-type (beq/bne/bgt/ble)
    51: MicroInstruction(action="signal_branch_r",
                         arg=None,
                         next_mpc="reset",
                         comment="beq/bne/bgt/ble: if cond PC += funct"),

    60: MicroInstruction(action="signal_jump",
                         next_mpc="reset",
                         comment="j: PC + jaddr"),

    61: MicroInstruction(action="signal_jal",
                         next_mpc="reset",
                         comment="jal: ra = PC; PC += imm"),

    62:MicroInstruction(action="signal_jr",
                        next_mpc="reset",
                        comment="jr: PC + rs1"),

    70:MicroInstruction(action="halt",
                        next_mpc="reset",
                        comment="halt: остановка")
}

# =================================================================
# DECODER — opcode → адрес микрокода
# =================================================================
DECODER: dict[int, int] = {
    0x00: 70,   # halt
    0x01: 10,   # R-type арифметика (add/sub/.../srl)
    0x02: 11,   # addi
    0x03: 11,   # andi
    0x04: 11,   # ori
    0x05: 11,   # xori
    0x06: 11,   # slli
    0x07: 11,   # srli
    0x08: 11,   # slti
    0x09: 12,   # lui
    0x0A: 20,   # lw
    0x0B: 30,   # sw
    0x0C: 50,   # beqz
    0x0D: 50,   # bnez
    0x0E: 51,   # beq
    0x0F: 51,   # bne
    0x10: 51,   # bgt
    0x11: 51,   # ble
    0x12: 60,   # j
    0x13: 61,   # jal
    0x14: 62,   # jr
    0x15: 40,   # mv
}

# =================================================================
# CONTROL UNIT
# =================================================================

class ControlUnit:
    def __init__(self, datapath: DataPath):
        self.dp = datapath
        self.mpc: int = 0
        self.tick: int = 0 # счетчик тактов(для логов)
        self.halted: bool = False

    def decode(self) -> int:
        """
        Декодер: opcode из IR → адрес блока микрокода.
        """
        opcode = self.dp.ir_opcode
        if opcode not in DECODER:
            raise ValueError(f"Неизвестный opcode {opcode}")
        return DECODER[opcode]
    def resolve_alu_op(self) -> str:
        """
        Для R-type арифметики (блок mPC=10) — определить операцию по funct.
        Для I-type арифметики (блок mPC=11) — по opcode.
        Возвращает строку для ALU.compute().
        """

        opcode = self.dp.ir_opcode

        if opcode == 0x01:
            funct = self.dp.ir_funct

            r_ops = {
                0x00: "add", 0x01: "sub", 0x02: "mul",
                0x03: "div", 0x04: "rem", 0x05: "and",
                0x06: "or", 0x07: "xor", 0x08: "sll",
                0x09: "srl",
            }
            return r_ops[funct]

        # I-type: операция по opcode
        i_ops = {
            0x02: "add",
            0x03: "and",
            0x04: "or",
            0x05: "xor",
            0x06: "sll",
            0x07: "srl",
            0x08: "slt",   # slti
        }
        return i_ops[opcode]
    def resolve_branch_taken(self) -> bool:
        """
        Вычислить выполнено ли условие ветвления
        """
        opcode = self.dp.ir_opcode

        # I-type: сравнение rs1 с нулём
        if opcode == 0x0C:
            return self.dp.regs.read(self.dp.ir_rs1) == 0
        if opcode == 0x0D:
            return self.dp.regs.read(self.dp.ir_rs1) != 0

        # R-type: сравнение rs1 и rs2
        a = self.dp.regs.read(self.dp.ir_rs1)
        b = self.dp.regs.read(self.dp.ir_rs2)

        if opcode == 0x0E: # beq
            return a == b
        if opcode == 0x0F: # bne
            return a != b
        if opcode == 0x10:  # bgt
            return a > b
        if opcode == 0x11:  # ble
            return a <= b

        raise ValueError(f"Не ветвление: opcode {opcode:#x}")


    def execute_tick(self) -> MicroInstruction:
        """
        Выполнить ОДИН такт.
        Возвращает выполненную микроинструкцию (для лога).
        """
        # 1. Читаем микроинструкцию по текущему mPC
        if self.mpc not in MICROCODE:
            raise ValueError(f"Нет микрокода по адресу mPC={self.mpc}")
        micro = MICROCODE[self.mpc]

        # 2. Исполняем действие
        action = micro.action

        if action == "halt":
            # Особый случай — поднимаем флаг остановки
            self.halted = True

        elif action == "signal_alu_r":
            # R-type: операцию определяем по funct прямо сейчас
            op = self.resolve_alu_op()
            self.dp.signal_alu_r(op)

        elif action == "signal_alu_i":
            # I-type: операцию по opcode
            op = self.resolve_alu_op()
            self.dp.signal_alu_i(op)

        elif action == "signal_branch_i":
            # Вычисляем условие и передаём в сигнал
            taken = self.resolve_branch_taken()
            self.dp.signal_branch_i(taken)

        elif action == "signal_branch_r":
            taken = self.resolve_branch_taken()
            self.dp.signal_branch_r(taken)

        elif action is not None:
            # Все остальные сигналы без аргументов:
            method = getattr(self.dp, action)
            method()

        # 3. Вычисляем следующий mPC
        if micro.next_mpc == "+1":
            self.mpc += 1
        elif micro.next_mpc == "decode":
            self.mpc = self.decode()
        elif micro.next_mpc == "reset":
            self.mpc = 0
        else:
            raise ValueError(f"Неизвестный переход mPC: {micro.next_mpc}")

        # 4. Увеличиваем счётчик тактов
        self.tick += 1

        return micro


# =================================================================
# SIMULATE — главный цикл
# =================================================================

def simulate(
        binary: bytes,
        input_str: str,
        memory_size: int = 0x1000,
        max_ticks: int = 100_000
) -> tuple[str, list[str]]:
    """
    Запускает программу на симуляторе.

    binary      — машинный код (с 4-байтным заголовком точки входа)
    input_str   — входные данные (строка, что подаётся в stdin)
    memory_size — размер памяти в байтах
    max_ticks   — предохранитель от бесконечного цикла

    Возвращает:
      output — то что программа вывела
      log    — список строк журнала (по одной на такт)
    """

    # Превращаем входную строку в список ASCII-кодов.
    input_tokens: list[int] = [ord(c) for c in input_str]

    memory = Memory(memory_size, input_tokens)
    entry_point = memory.load(binary)

    datapath = DataPath(memory, start_pc=entry_point)
    cu = ControlUnit(datapath)

    log: list[str] = []

    # Главный цикл тактов
    while not cu.halted and cu.tick < max_ticks:
        # Запоминаем состояние до такта для лога
        tick_num = cu.tick
        mpc_before = cu.mpc

        try:
            # Выполняем один такт
            micro = cu.execute_tick()

        except StopIteration:
            # Входной буфер пуст (EOF при чтении из 0x80) — нормальный конец
            log.append(f"--- EOF на такте {tick_num}, останов ---")
            break

        # Формируем строку журнала.
        log_line = (
            f"TICK {tick_num:>4} | "
            f"mPC={mpc_before:>3} | "
            f"{datapath.dump()} | "
            f"{micro.comment}"
        )
        log.append(log_line)

    # Проверка предохранителя.
    if cu.tick >= max_ticks:
        log.append(f"--- ПРЕВЫШЕН ЛИМИТ ТАКТОВ ({max_ticks}) ---")

    return memory.get_output(), log


# =================================================================
# MAIN — запуск из командной строки
# =================================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Использование: python machine.py <program.bin> [input.txt]")
        sys.exit(1)

    bin_path = sys.argv[1]

    # Входные данные: второй аргумент — файл с вводом (необязательный).
    input_data = ""
    if len(sys.argv) >= 3:
        with open(sys.argv[2], encoding="utf-8") as f:
            input_data = f.read()

    # Читаем бинарник
    with open(bin_path, "rb") as f:
        binary = f.read()

    output, log = simulate(binary, input_data)

    # Печатаем журнал
    print("=" * 70)
    print("ЖУРНАЛ ВЫПОЛНЕНИЯ:")
    print("=" * 70)
    for line in log:
        print(line)

    # Печатаем результат
    print("=" * 70)
    print("ВЫВОД ПРОГРАММЫ:")
    print("=" * 70)
    print(repr(output))
    print()
    print("Как текст:")
    print(output)
