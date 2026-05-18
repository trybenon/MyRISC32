OPCODES : dict[str, int] = {
    "halt" : 0x00,
    # R-type различаются funct
    "add":  0x01, "sub":  0x01, "mul":  0x01,
    "div":  0x01, "rem":  0x01,
    "and":  0x01, "or":   0x01, "xor":  0x01,
    "sll":  0x01, "srl":  0x01,
    # I-type арифметика
    "addi" : 0x02, "andi": 0x03, "ori": 0x04,
    "xori": 0x05, "slli": 0x06, "srli": 0x07,
    "slti": 0x08, "lui":  0x09,
    # Память
    "lw": 0x0A, "sw": 0x0B,
    # Ветвления I-type (один операнд)
    "beqz": 0x0C, "bnez": 0x0D,
    # Ветвления R-type (два операнда)
    "beq":  0x0E, "bne":  0x0F,
    "bgt":  0x10, "ble":  0x11,
    # Переходы
    "j":    0x12, "jal":  0x13, "jr":   0x14,
    # Прочее
    "mv":   0x15,
}

FUNCT: dict[str, int] = {
    "add": 0x00, "sub": 0x01, "mul": 0x02,
    "div": 0x03, "rem": 0x04,
    "and": 0x05, "or":  0x06, "xor": 0x07,
    "sll": 0x08, "srl": 0x09,
}

REGISTERS: dict[str, int] = {
    "zero": 0, "r0": 0,
    "ra":   1, "r1": 1,
    "sp":   2, "r2": 2,
    "t0":   3, "r3": 3,
    "t1":   4, "r4": 4,
    "a0":   5, "r5": 5,
    "a1":   6, "r6": 6,
    "a2":   7, "r7": 7,
}

R_TYPE: set[str] = {
    "add", "sub", "mul", "div", "rem",
    "and", "or",  "xor", "sll", "srl",
    "beq", "bne", "bgt", "ble",
}

I_TYPE: set[str] = {
    "addi", "andi", "ori", "xori", "slli", "srli", "slti", "lui",
    "lw", "sw",
    "beqz", "bnez",
    "jal", "jr", "mv",
}

J_TYPE: set[str] = {"j"}

PSEUDO: set[str] = {"nop", "ret", "call", "li", "la"}

IO_IN:  int = 0x80
IO_OUT: int = 0x84

