/* Original direct-trap probe, usable on IRIX and the Xiri static subset.
 * Each observation is sixteen big-endian words: magic, case, v0, v1, a3,
 * guard, six capability words, and four trailing guards. No libc is used. */
    .set noreorder
    .set noat
    .section .note.probe,"a",@note
    .long 5, 4, 0x49524958
    .asciz "Xiri"
    .balign 4
    .long 1

    .macro address reg, label
    lui \reg, %hi(\label)
    addiu \reg, \reg, %lo(\label)
    .endm
    .macro begin number
    li $a0, \number
    jal prepare
    nop
    .endm
    .macro observe number
    li $v0, \number
    li $v1, 0xfeedface
    syscall
    nop
    sw $v0, 40($sp)
    sw $v1, 44($sp)
    sw $a3, 48($sp)
    li $v0, 1004
    li $a0, 1
    addiu $a1, $sp, 32
    li $a2, 64
    syscall
    nop
    bnez $a3, failed
    nop
    li $t0, 64
    bne $v0, $t0, failed
    nop
    .endm

    .text
    .globl _start
_start:
    lw $t0, 0($sp)
    addiu $sp, $sp, -128
    li $t1, 1
    beq $t0, $t1, unpriv_done
    nop
    /* Optional reference-only setup: the same binary can run as uid/gid
     * 60001 on original IRIX. Xiri tests set credentials in the native parent. */
    li $a0, 60001
    li $v0, 1046
    syscall
    nop
    bnez $a3, failed
    nop
    li $a0, 60001
    li $v0, 1023
    syscall
    nop
    bnez $a3, failed
    nop
unpriv_done:
    begin 1
    li $a0, 22
    li $a1, 29
    observe 1040
    begin 2
    li $a0, 22
    li $a1, 11
    observe 1040
    begin 3
    li $a0, 22
    li $a1, 0x7fffffff
    observe 1040
    begin 4
    li $a0, 85
    address $a1, cap_name
    addiu $a2, $sp, 56
    observe 1040
    begin 5
    li $a0, 85
    address $a1, unknown_name
    addiu $a2, $sp, 56
    observe 1040
    begin 6
    li $a0, 85
    move $a1, $zero
    addiu $a2, $sp, 56
    observe 1040
    begin 7
    li $a0, 85
    address $a1, cap_name
    move $a2, $zero
    observe 1040
    begin 8
    observe 1024
    begin 9
    observe 1047
    begin 10
    li $a0, 0x7fffffff
    observe 1040
    begin 11
    li $a0, 85
    li $a1, 1
    addiu $a2, $sp, 56
    observe 1040
    begin 12
    li $a0, 85
    address $a1, cap_name
    li $a2, 1
    observe 1040
    begin 13
    li $a0, 85
    address $a1, cap_name
    address $a2, cap_name
    observe 1040
    begin 14
    li $a0, 85
    address $a1, long_name
    addiu $a2, $sp, 56
    observe 1040
    begin 15
    li $a0, 85
    address $a1, name_79
    addiu $a2, $sp, 56
    observe 1040
    begin 16
    li $a0, 85
    address $a1, name_80
    addiu $a2, $sp, 56
    observe 1040
    li $a0, 0
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

prepare:
    addiu $t0, $sp, 32
    addiu $t1, $sp, 96
    li $t2, 0xa5a5a5a5
2:  sw $t2, 0($t0)
    addiu $t0, $t0, 4
    bne $t0, $t1, 2b
    nop
    li $t0, 0x58495131
    sw $t0, 32($sp)
    sw $a0, 36($sp)
    move $a0, $zero
    move $a1, $zero
    move $a2, $zero
    move $a3, $zero
    sw $zero, 16($sp)
    sw $zero, 20($sp)
    jr $ra
    nop
    .section .rodata
cap_name:
    .asciz "SGI_CAP_PROCESS"
unknown_name:
    .asciz "XIRI_UNKNOWN"
long_name:
    .fill 256, 1, 0x41
    .byte 0
name_79:
    .fill 79, 1, 0x41
    .byte 0
name_80:
    .fill 80, 1, 0x41
    .byte 0
