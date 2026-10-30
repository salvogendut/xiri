/* Original dual-ABI heap fixtures. Initial data ends at 0x00802000 on
 * both 4 KiB and 8 KiB kernels. No libc, vendor code, or implicit GP. */
    .set noreorder
    .set noat
    .section .note.probe,"a",@note
    .long 5, 4, 0x49524958
    .asciz "Xiri"
    .balign 4
    .long 1
    .macro heap end
    li $a0, \end
    .if INDIRECT
    move $a1, $a0
    li $a0, 1017
    li $v0, 1000
    .else
    li $v0, 1017
    .endif
    li $v1, 0xfeedface
    syscall
    nop
    .endm
    .macro goodheap end
    heap \end
    bnez $a3, failed
    nop
    bnez $v0, failed
    nop
    .endm
    .text
    .globl _start
_start:
    addiu $sp, $sp, -128
    li $s6, 0
    .ifdef CYCLE
    goodheap 0x00806001
    li $s0, 0x00802000
    lw $12, 0($s0)
    bnez $12, failed
    nop
    li $12, 0x12345678
    sw $12, 0($s0)
    li $s1, 0x00806000
    lw $12, 0($s1)
    bnez $12, failed
    nop
    li $12, 0x76543210
    sw $12, 0($s1)
    goodheap 0x00804000
    lw $12, 0($s0)
    li $13, 0x12345678
    bne $12, $13, failed
    nop
    .ifdef FAULT
    lw $12, 0($s1)
    b failed
    nop
    .endif
    goodheap 0x00806001
    lw $12, 0($s1)
    bnez $12, failed
    nop
    goodheap 0x00802000
    li $s6, 1
    .else
    .ifdef COLLISION
    lui $a0, %hi(zero_path)
    addiu $a0, $a0, %lo(zero_path)
    li $a1, 0
    li $a2, 0
    li $v0, 1005
    syscall
    nop
    bnez $a3, failed
    nop
    sw $v0, 16($sp)
    move $8, $v0
    sw $zero, 20($sp)
    move $9, $zero
    li $a0, 0x00804000
    li $a1, 8192
    li $a2, 3
    li $a3, 2 /* A free MAP_PRIVATE hint, checked below. */
    li $v0, 1134
    syscall
    nop
    bnez $a3, failed
    nop
    li $s0, 0x00804000
    bne $v0, $s0, failed
    nop
    li $12, 0x12345678
    sw $12, 0($s0)
    .endif
    heap END
    .ifdef COLLISION
    lw $12, 0($s0)
    li $13, 0x12345678
    bne $12, $13, failed
    nop
    li $s6, 1
    .endif
    .endif
    sw $v0, 40($sp)
    sw $v1, 44($sp)
    sw $a3, 48($sp)
    /* A rejected heap request must leave initialized data intact. */
    lui $12, %hi(data_word)
    lw $12, %lo(data_word)($12)
    li $13, 0x13579bdf
    bne $12, $13, failed
    nop
    li $12, 0x58494431
    sw $12, 32($sp)
    li $12, CASE
    sw $12, 36($sp)
    sw $s6, 52($sp)
    sw $zero, 56($sp)
    sw $zero, 60($sp)
    li $a0, 1
    addiu $a1, $sp, 32
    li $a2, 32
    li $v0, 1004
    syscall
    nop
    bnez $a3, failed
    nop
    li $12, 32
    bne $v0, $12, failed
    nop
    li $a0, 0
    b finish
    nop
failed:
    li $a0, 99
finish:
    li $v0, 1001
    syscall
    nop
    .section .rodata
zero_path:
    .asciz "/dev/zero"
    .data
data_word:
    .long 0x13579bdf
