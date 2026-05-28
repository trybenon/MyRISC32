.data
msg: .cstr "Hello, World!\n"

.text
.org 0x100
_start:
    la   t0, msg
    la   t1, out_addr
    lw   t1, 0(t1)

loop:
    lw   a0, 0(t0)
    beqz a0, done
    sw   a0, 0(t1)
    addi t0, t0, 1
    j    loop

done:
    halt

.data
out_addr: .word 0x84