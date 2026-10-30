/* Original synthetic interpreter; verifies the dynamic loader before libc. */
    .set noreorder
    .set noat
    .text
    .globl _start
_start:
    andi $t0, $sp, 7
    bnez $t0, failed
    nop
    lw $t0, 0($sp)
    li $t1, 1
    bne $t0, $t1, failed
    nop
    lw $t0, 4($sp)
    andi $t0, $t0, 15
    bnez $t0, failed
    nop
    lw $t0, 8($sp)       /* argv terminator */
    lw $t1, 12($sp)      /* empty environment */
    or $t0, $t0, $t1
    bnez $t0, failed
    nop
    addiu $t0, $sp, 16
    lui $t1, %hi(expected_aux)
    addiu $t1, $t1, %lo(expected_aux)
    li $t2, 14
1:  lw $t3, 0($t0)
    lw $t4, 0($t1)
    bne $t3, $t4, failed
    nop
    addiu $t0, $t0, 4
    addiu $t1, $t1, 4
    addiu $t2, $t2, -1
    bnez $t2, 1b
    nop

    /* Initialized data, partial-page BSS, and the next BSS page in both
     * images; poison bytes follow p_filesz in the on-disk fixtures. */
    li $s0, 0x10004000
    li $s1, 0x0f904000
    li $t4, 0x12345678
    li $t5, 2
2:  lw $t0, 0($s0)
    bne $t0, $t4, failed
    nop
    addiu $t1, $s0, 4
    addiu $t2, $s0, 0x1010
3:  lbu $t0, 0($t1)
    bnez $t0, failed
    nop
    li $t0, 0xa7
    sb $t0, 0($t1)
    lbu $t3, 0($t1)
    bne $t0, $t3, failed
    nop
    addiu $t1, $t1, 1
    bne $t1, $t2, 3b
    nop
    addiu $t5, $t5, -1
    move $s0, $s1
    bnez $t5, 2b
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
    .long 7, 0x0f900000, 6, 4096, 0, 0
