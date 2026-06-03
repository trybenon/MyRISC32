; Читает символы из stdin, выводит в stdout, до EOF (0)

.data
in_addr:  .word 0x80
out_addr: .word 0x84

.text
_start:
    la   t0, in_addr
    lw   t0, 0(t0)

    la   t1, out_addr
    lw   t1, 0(t1)

loop:
    lw   a0, 0(t0)
    beqz a0, done
    sw   a0, 0(t1)
    j    loop

done:
