/* Original synthetic interpreter; verifies the dynamic loader before libc. */
    .set noreorder
    .set noat
    .text
    .globl _start
_start:
    andi $12, $sp, 7
    bnez $12, failed
    nop
    lw $12, 0($sp)
    li $13, 1
    bne $12, $13, failed
    nop
    lw $12, 4($sp)
    andi $12, $12, 15
    bnez $12, failed
    nop
    lw $12, 8($sp)       /* argv terminator */
    lw $13, 12($sp)      /* empty environment */
    or $12, $12, $13
    bnez $12, failed
    nop
    addiu $12, $sp, 16
    lui $13, %hi(expected_aux)
    addiu $13, $13, %lo(expected_aux)
    li $14, 14
1:  lw $15, 0($12)
    lw $24, 0($13)
    bne $15, $24, failed
    nop
    addiu $12, $12, 4
    addiu $13, $13, 4
    addiu $14, $14, -1
    bnez $14, 1b
    nop

    /* Initialized data, partial-page BSS, and the next BSS page in both
     * images; poison bytes follow p_filesz in the on-disk fixtures. */
    li $s0, 0x10004000
    li $s1, 0x0f904000
    li $24, 0x12345678
    li $25, 2
2:  lw $12, 0($s0)
    bne $12, $24, failed
    nop
    addiu $13, $s0, 4
    addiu $14, $s0, 0x2010
3:  lbu $12, 0($13)
    bnez $12, failed
    nop
    li $12, 0xa7
    sb $12, 0($13)
    lbu $15, 0($13)
    bne $12, $15, failed
    nop
    addiu $13, $13, 1
    bne $13, $14, 3b
    nop
    addiu $25, $25, -1
    move $s0, $s1
    bnez $25, 2b
    nop
    li $t9, 0x00401000
    jr $t9
    nop
failed:
    li $a0, 99
    li $v0, 1001
    syscall
    nop
4:  b 4b
    nop
    .balign 4
expected_aux:
    .long 3, 0x00400034, 4, 32, 5, 5, 9, 0x00401000
    .long 7, 0x0f900000, 6, 8192, 0, 0
