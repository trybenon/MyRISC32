; sort.asm — пузырьковая сортировка чисел
; Вход: числа через stdin, каждое на новой строке, 0 = конец массива
; Выход: числа в порядке возрастания, каждое на новой строке
;
; Пример:
;   in:  5\n3\n1\n4\n2\n0\n
;   out: 1\n2\n3\n4\n5\n

.data
.org 0x100
in_addr:   .word 0x80
out_addr:  .word 0x84

; массив до 64 элементов
array:
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
    .word 0
    .word 0

count: .word 0

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

_start:
    li   sp, 0xE00

    ; --- Чтение чисел в массив ---
    la   t0, array               ; t0 = указатель в массив
    addi t1, zero, 0             ; t1 = счётчик элементов

read_loop:
    ; сохраняем t0, t1 — read_int затрёт регистры
    addi sp, sp, -8
    sw   t0, 0(sp)
    sw   t1, 4(sp)

    jal  read_int                ; a0 = прочитанное число

    lw   t1, 4(sp)
    lw   t0, 0(sp)
    addi sp, sp, 8

    beqz a0, read_done           ; 0 — конец ввода
    sw   a0, 0(t0)               ; array[i] = число
    addi t0, t0, 4
    addi t1, t1, 1
    j    read_loop

read_done:
    ; сохраняем count
    la   t0, count
    sw   t1, 0(t0)

    ; --- Пузырьковая сортировка ---
    ; n = t1
    ; for i = 0; i < n-1; i++:
    ;   for j = 0; j < n-i-1; j++:
    ;     if array[j] > array[j+1]: swap
    ;
    ; Регистры:
    ;   a0 = n
    ;   a1 = i
    ;   a2 = j
    ;   t0, t1 — временные

    mv   a0, t1                  ; a0 = n
    addi a1, zero, 0             ; i = 0

outer:
    ; if i >= n-1: конец
    addi t0, a0, -1              ; t0 = n-1
    ble  t0, a1, sort_done       ; n-1 <= i → выходим

    addi a2, zero, 0             ; j = 0

inner:
    ; if j >= n-i-1: следующий i
    sub  t0, a0, a1              ; t0 = n - i
    addi t0, t0, -1              ; t0 = n - i - 1
    ble  t0, a2, inner_done      ; n-i-1 <= j → выходим

    ; адрес array[j] = array + j*4
    la   t0, array
    slli t1, a2, 2               ; t1 = j*4
    add  t0, t0, t1              ; t0 = &array[j]

    ; читаем array[j] и array[j+1]
    lw   t1, 0(t0)               ; t1 = array[j]
    lw   ra, 4(t0)               ; ra = array[j+1] (ra сейчас не нужен)

    ; if array[j] <= array[j+1]: не swap
    ble  t1, ra, no_swap

    ; swap
    sw   ra, 0(t0)               ; array[j] = array[j+1]
    sw   t1, 4(t0)               ; array[j+1] = array[j]

no_swap:
    addi a2, a2, 1               ; j++
    j    inner

inner_done:
    addi a1, a1, 1               ; i++
    j    outer

sort_done:
    ; --- Вывод массива ---
    ; для каждого элемента: print_int + '\n'
    addi a1, zero, 0             ; i = 0

print_array:
    ble  a0, a1, print_done     ; i >= n → конец

    ; сохраняем счётчики
    addi sp, sp, -8
    sw   a0, 0(sp)
    sw   a1, 4(sp)

    ; читаем array[i]
    la   t0, array
    slli t1, a1, 2
    add  t0, t0, t1
    lw   a0, 0(t0)               ; a0 = array[i]

    jal  print_int

    ; \n
    la   a2, out_addr
    lw   a2, 0(a2)
    addi a0, zero, 10
    sw   a0, 0(a2)

    lw   a1, 4(sp)
    lw   a0, 0(sp)
    addi sp, sp, 8

    addi a1, a1, 1
    j    print_array

print_done:
    halt


; read_int() -> a0
;   Читает символы из stdin до \n, собирает десятичное число.
;   Регистры:
;     t0 — порт ввода
;     t1 — текущий символ
;     a0 — накапливаемое число
;     a1 — константа 10
;     a2 — временный (цифра)

read_int:
    la   t0, in_addr
    lw   t0, 0(t0)               ; t0 = 0x80
    addi a0, zero, 0             ; число = 0
    addi a1, zero, 10

ri_loop:
    lw   t1, 0(t0)               ; читаем символ
    addi a2, t1, -10             ; сравниваем с '\n'
    beqz a2, ri_done             ; \n — конец числа

    ; цифра: a0 = a0*10 + (t1 - 48)
    mul  a0, a0, a1
    addi t1, t1, -48             ; ASCII → цифра
    add  a0, a0, t1
    j    ri_loop

ri_done:
    jr   ra


; print_int(a0): печать числа в десятичном виде

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