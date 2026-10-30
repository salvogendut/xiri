/* Original n32 FR=1 and full-width GPR test through the foreign dispatcher. */
    .set noreorder
    .set noat
    .set fp=64
    .section .note.probe,"a",@note
    .long 5, 4, 0x49524958
    .asciz "Xiri"
    .balign 4
    .long 1
    .text
    .globl _start
_start:
    dli $s0, 0x1234567887654321
    dli $12, 0x3ff0000000000000
    dmtc1 $12, $f1
    dli $12, 0x4000000000000000
    dmtc1 $12, $f3
    nop
    add.d $f5, $f1, $f3
    li $v0, 1024
    syscall
    nop
    bnez $a3, failed
    nop
    dli $12, 0x1234567887654321
    bne $s0, $12, failed
    nop
    dmfc1 $13, $f5
    dli $12, 0x4008000000000000
    bne $13, $12, failed
    nop
    dmfc1 $13, $f1
    dli $12, 0x3ff0000000000000
    bne $13, $12, failed
    nop
    li $a0, 1
    lui $a1, %hi(message)
    addiu $a1, $a1, %lo(message)
    li $a2, 15
    li $v0, 1004
    syscall
    nop
    bnez $a3, failed
    nop
    li $a0, 37
    b finish
    nop
failed:
    li $a0, 99
finish:
    li $v0, 1001
    syscall
    nop
1:  b 1b
    nop
    .section .rodata
message: .ascii "XIRI_N32_FP_OK\n"
