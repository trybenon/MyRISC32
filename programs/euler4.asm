; Euler 4: наибольший палиндром = произведение двух 3-значных
; Ответ: 906609 = 913 * 993

.data
.org 0x100
out_addr:  .word 0x84

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
; Главная: два вложенных цикла i = 999..100, j = i..100
; a1 = max, t0 = i, t1 = j, a2 = i*j
_start:
    la      sp, 0x800
    addi    a1, zero, 0          ; max = 0
    li      t0, 999              ; i = 999

outer_loop:
    slti    a0, t0, 100
    bnez    a0, done             ; i < 100 — конец
    mv      t1, t0               ; j = i

inner_loop:
    slti    a0, t1, 100
    bnez    a0, outer_next       ; j < 100 — следующий i
    mul     a2, t0, t1           ; p = i*j
    ble     a2, a1, outer_next   ; p <= max — дальше будет только меньше

    ; вызов is_palindrome: сохраняем то что затрётся
    addi    sp, sp, -16
    sw      a1, 0(sp)
    sw      t0, 4(sp)
    sw      t1, 8(sp)
    sw      a2, 12(sp)

    mv      a0, a2
    jal     is_palindrome        ; a0 = 1 если палиндром

    lw      a2, 12(sp)
    lw      t1, 8(sp)
    lw      t0, 4(sp)
    lw      a1, 0(sp)
    addi    sp, sp, 16

    beqz    a0, inner_next       ; не палиндром — следующая j
    mv      a1, a2               ; обновляем max

inner_next:
    addi    t1, t1, -1
    j       inner_loop

outer_next:
    addi    t0, t0, -1
    j       outer_loop

done:
    mv      a0, a1
    jal     print_int

    ; перевод строки
    la      a2, out_addr
    lw      a2, 0(a2)
    addi    a0, zero, 10
    sw      a0, 0(a2)

    halt


; ----------------------------------------------------------------
; is_palindrome(a0) -> a0: разворачиваем число и сравниваем
; ----------------------------------------------------------------
is_palindrome:
    bnez a0, ip_init
    addi a0, zero, 1             ; 0 считаем палиндромом
    jr   ra

ip_init:
    mv   t0, a0                  ; original
    addi t1, zero, 0             ; reversed = 0
    addi a1, zero, 10

ip_loop:
    rem  a2, a0, a1              ; цифра = n % 10
    mul  t1, t1, a1              ; reversed *= 10
    add  t1, t1, a2              ; reversed += цифра
    div  a0, a0, a1              ; n /= 10
    bnez a0, ip_loop

    addi a0, zero, 0
    bne  t1, t0, ip_done         ; не равны — выходим с 0
    addi a0, zero, 1             ; равны — палиндром

ip_done:
    jr   ra


; ----------------------------------------------------------------
; print_int(a0): печатает число в stdout
; Извлекаем цифры в буфер, потом печатаем буфер с конца
; ----------------------------------------------------------------
print_int:
    bnez a0, pi_init
    ; особый случай — число 0
    la   a2, out_addr
    lw   a2, 0(a2)
    addi a0, zero, 48            ; '0'
    sw   a0, 0(a2)
    jr   ra

pi_init:
    la   a2, out_addr
    lw   a2, 0(a2)
    addi a1, zero, 10
    la   t0, digit_buf
    addi t1, zero, 0             ; счётчик цифр

pi_extract_loop:
    ; нужны и n и цифра — пушим n на стек, считаем цифру в a0
    addi sp, sp, -4
    sw   a0, 0(sp)
    rem  a0, a0, a1              ; цифра
    addi a0, a0, 48              ; в ASCII
    sw   a0, 0(t0)               ; в буфер
    addi t0, t0, 4
    addi t1, t1, 1
    lw   a0, 0(sp)
    addi sp, sp, 4
    div  a0, a0, a1              ; n /= 10
    bnez a0, pi_extract_loop

pi_print_loop:
    addi t0, t0, -4              ; назад по буферу
    lw   a0, 0(t0)
    sw   a0, 0(a2)
    addi t1, t1, -1
    bnez t1, pi_print_loop
    jr   ra