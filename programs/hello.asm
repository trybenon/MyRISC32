; hello: выводит "Hello, World!\n" в stdout

.data
.org 0x100
msg:       .cstr "Hello, World!\n"
out_addr:  .word 0x84

.text
; Регистры:
;   t0 — указатель текущего символа строки
;   t1 — адрес порта вывода
;   a0 — текущий символ
_start:
    la   t1, out_addr
    lw   t1, 0(t1)               ; t1 = 0x84

    la   t0, msg                 ; t0 = адрес строки

loop:
    lw   a0, 0(t0)               ; читаем символ
    beqz a0, done                ; \0 — конец строки
    sw   a0, 0(t1)               ; пишем в stdout
    addi t0, t0, 4               ; следующий символ
    j    loop

done:
    halt