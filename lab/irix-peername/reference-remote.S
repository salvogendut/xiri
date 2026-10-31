/* Original IRIX-only server-address peer for paired getpeername probes. */
    .set noreorder
    .section .note.probe,"a",@note
    .long 5, 4, 0x49524958
    .asciz "Xiri"
    .balign 4
    .long 1
    .macro checked number
    li $v0, \number
    syscall
    nop
    bnez $a3, failed
    nop
    .endm
    .text
    .globl _start
_start:
    addiu $sp, $sp, -256
    li $a0, 2
    li $a1, 2
    move $a2, $zero
    checked 1107
    move $s0, $v0
    li $8, 0x000217e1 /* family 2, port 6113 */
    sw $8, 64($sp)
    li $8, 0x7f000001
    sw $8, 68($sp)
    sw $zero, 72($sp)
    sw $zero, 76($sp)
    move $a0, $s0
    addiu $a1, $sp, 64
    li $a2, 16
    checked 1090
    move $a0, $s0
    li $a1, 4
    checked 1096
    li $8, 0x5244590a
    sw $8, 80($sp)
    li $a0, 1
    addiu $a1, $sp, 80
    li $a2, 4
    checked 1004
    li $s4, COUNT
accept:
    move $a0, $s0
    move $a1, $zero
    move $a2, $zero
    checked 1089
    move $s1, $v0
    move $a0, $s1
    addiu $a1, $sp, 96
    addiu $a2, $sp, 112
    li $8, 16
    sw $8, 112($sp)
    checked 1094
    lw $8, 112($sp)
    li $9, 16
    bne $8, $9, failed
    nop
    li $s2, 16
    addiu $s3, $sp, 96
write:
    move $a0, $s1
    move $a1, $s3
    move $a2, $s2
    checked 1004
    blez $v0, failed
    nop
    subu $s2, $s2, $v0
    addu $s3, $s3, $v0
    bnez $s2, write
    nop
    /* Keep the accepted connection alive until the query client closes it. */
    move $a0, $s1
    addiu $a1, $sp, 128
    li $a2, 1
    checked 1003
    bnez $v0, failed
    nop
    move $a0, $s1
    checked 1006
    addiu $s4, $s4, -1
    bnez $s4, accept
    nop
    move $a0, $s0
    checked 1006
    move $a0, $zero
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
