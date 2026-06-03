; hello_user_name: спрашивает имя и здоровается
; Поток: "What is your name?\n" → читаем имя до \n → "Hello, <name>!\n"

.data
.org 0x100
out_addr:  .word 0x84
in_addr:   .word 0x80

prompt:    .cstr "What is your name?\n"
greeting:  .cstr "Hello, "
exclaim:   .cstr "!\n"

; буфер для имени — 32 символа максимум
name_buf:
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

.text
; Регистры:
;   t1 — адрес порта ввода (0x80)
;   a1 — адрес порта вывода (0x84)
;   t0 — указатель текущего символа строки
;   a0 — текущий символ
_start:
    ; готовим адреса портов один раз
    la   t1, in_addr
    lw   t1, 0(t1)
    la   a1, out_addr
    lw   a1, 0(a1)

    ; --- печать "What is your name?\n" ---
    la   t0, prompt
print_prompt:
    lw   a0, 0(t0)
    beqz a0, read_name           ; \0 — строка кончилась
    sw   a0, 0(a1)
    addi t0, t0, 4
    j    print_prompt

    ; --- чтение имени в буфер до \n ---
read_name:
    la   t0, name_buf
read_loop:
    lw   a0, 0(t1)               ; читаем символ
    addi a2, a0, -10             ; сравниваем с '\n' (10)
    beqz a2, end_read            ; если \n — стоп
    sw   a0, 0(t0)               ; иначе пишем в буфер
    addi t0, t0, 4
    j    read_loop
end_read:
    sw   zero, 0(t0)             ; null-terminator в конце имени

    ; --- "Hello, " ---
    la   t0, greeting
print_greeting:
    lw   a0, 0(t0)
    beqz a0, print_name
    sw   a0, 0(a1)
    addi t0, t0, 4
    j    print_greeting

    ; --- имя из буфера ---
print_name:
    la   t0, name_buf
print_name_loop:
    lw   a0, 0(t0)
    beqz a0, print_exclaim
    sw   a0, 0(a1)
    addi t0, t0, 4
    j    print_name_loop

    ; --- "!\n" ---
print_exclaim:
    la   t0, exclaim
print_exclaim_loop:
    lw   a0, 0(t0)
    beqz a0, done
    sw   a0, 0(a1)
    addi t0, t0, 4
    j    print_exclaim_loop

done:
    halt