"""Тесты для транслятора."""

from isa import FUNCT, OPCODES, REGISTERS
from translator import encode_i, encode_r, encode_u


def test_encode_addi():
    """addi a0, zero, 42 → корректный байт-код."""
    # opcode=0x02, rd=5(a0), rs1=0(zero), imm=42
    result = encode_i(OPCODES["addi"], REGISTERS["a0"], REGISTERS["zero"], 42)
    word = int.from_bytes(result, "big")

    # Проверяем поля по битам
    assert (word >> 25) & 0x7F == 0x02  # opcode
    assert (word >> 22) & 0x7 == 5  # rd = a0
    assert (word >> 19) & 0x7 == 0  # rs1 = zero
    assert word & 0x7FFFF == 42  # imm


def test_encode_add():
    """add a0, a1, a2 → корректный байт-код."""
    result = encode_r(
        OPCODES["add"],
        REGISTERS["a0"], REGISTERS["a1"], REGISTERS["a2"],
        FUNCT["add"]
    )
    word = int.from_bytes(result, "big")

    assert (word >> 25) & 0x7F == 0x01  # R-type opcode
    assert (word >> 22) & 0x7 == 5  # rd = a0
    assert (word >> 19) & 0x7 == 6  # rs1 = a1
    assert (word >> 16) & 0x7 == 7  # rs2 = a2
    assert word & 0xFFFF == FUNCT["add"]


def test_encode_lui():
    """lui a0, 0x12345 → U-type, 22-битное поле."""
    result = encode_u(OPCODES["lui"], REGISTERS["a0"], 0x12345)
    word = int.from_bytes(result, "big")

    assert (word >> 25) & 0x7F == 0x09
    assert (word >> 22) & 0x7 == 5
    assert word & 0x3FFFFF == 0x12345


def test_encode_negative_immediate():
    """addi с отрицательным imm — должна работать маска."""
    # addi t0, t0, -1
    result = encode_i(OPCODES["addi"], 3, 3, -1)
    word = int.from_bytes(result, "big")

    # -1 в 19 битах = 0x7FFFF
    assert word & 0x7FFFF == 0x7FFFF
