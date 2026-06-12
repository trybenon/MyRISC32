; double_precision.asm
; Демонстрация 64-битной арифметики через пары 32-битных слов.
;
; Складываем:
;    A = 0x00000001 00000005  (≈ 4 294 967 301)
;  + B = 0x00000002 FFFFFFFF  (≈ 12 884 901 887)
;  = C = 0x00000004 00000004  (≈ 17 179 869 188)
;
; Выводим результат в шестнадцатеричном виде как: HI:LO

.data
.org 0x100
out_addr:  .word 0x84

; Операнд A: hi, lo
A_hi:      .word 1
A_lo:      .word 5

; Операнд B: hi, lo
B_hi:      .word 2
B_lo:      .word -1

; Результат
C_hi:      .word 0
C_lo:      .word 0

digit_buf:
    .word 0
    .word 0
    .word 0
    .word 0
    .word 0
    .word 0
    .word 0
    .word 0
    .word 0
    .word 0

.text
; Регистры:
;   t0 — A_lo
;   t1 — B_lo
;   a1 — A_hi
;   a2 — B_hi
;   a0 — временный
_start:
    li   sp, 0xE00

    ; --- Загружаем операнды ---
    la   t0, A_lo
    lw   t0, 0(t0)               ; t0 = A_lo = 5
    la   t1, B_lo
    lw   t1, 0(t1)               ; t1 = B_lo = -1 (0xFFFFFFFF)

    la   a1, A_hi
    lw   a1, 0(a1)               ; a1 = A_hi = 1
    la   a2, B_hi
    lw   a2, 0(a2)               ; a2 = B_hi = 2

    ; --- Складываем младшие части ---
    add  a0, t0, t1              ; a0 = A_lo + B_lo
                                 ; 5 + (-1) = 4  (но беззнаково был перенос!)

    ; Сохраняем lo результата
    la   t0, C_lo
    sw   a0, 0(t0)

    ; --- Определяем carry ---
    ; Если результат < A_lo (беззнаково), был перенос
    ; Для общего случая используем slt:
    ;   carry = (result < A_lo) ? 1 : 0

    la   t0, A_lo
    lw   t0, 0(t0)               ; t0 = A_lo снова
    ; a0 - сумма

    addi t1, zero, 0             ; carry = 0
    bgt  t0, a0, set_carry       ; если A_lo > результат => был перенос
    j    no_carry
set_carry:
    addi t1, zero, 1             ; carry = 1
no_carry:

    ; --- Складываем старшие части с переносом ---
    add  a1, a1, a2              ; hi = A_hi + B_hi = 1 + 2 = 3
    add  a1, a1, t1              ; hi += carry = 3 + 1 = 4

    la   t0, C_hi
    sw   a1, 0(t0)

    ; --- Вывод: "HI:LO\n" ---

    ; HI
    mv   a0, a1                  ; a0 = hi
    jal  print_int

    ; ':'
    la   a2, out_addr
    lw   a2, 0(a2)
    addi a0, zero, 58            ; ':' = 58
    sw   a0, 0(a2)

    ; LO
    la   t0, C_lo
    lw   a0, 0(t0)
    jal  print_int

    ; \n
    la   a2, out_addr
    lw   a2, 0(a2)
    addi a0, zero, 10
    sw   a0, 0(a2)

    halt



print_int:
    bnez a0, pi_init
    la   a2, out_addr
    lw   a2, 0(a2)
    addi a0, zero, 48
    sw   a0, 0(a2)
    jr   ra
pi_init:
    la   a2, out_addr
    lw   a2, 0(a2)
    addi a1, zero, 10
    la   t0, digit_buf
    addi t1, zero, 0
pi_extract_loop:
    addi sp, sp, -4
    sw   a0, 0(sp)
    rem  a0, a0, a1
    addi a0, a0, 48
    sw   a0, 0(t0)
    addi t0, t0, 4
    addi t1, t1, 1
    lw   a0, 0(sp)
    addi sp, sp, 4
    div  a0, a0, a1
    bnez a0, pi_extract_loop
pi_print_loop:
    addi t0, t0, -4
    lw   a0, 0(t0)
    sw   a0, 0(a2)
    addi t1, t1, -1
    bnez t1, pi_print_loop
    jr   ra