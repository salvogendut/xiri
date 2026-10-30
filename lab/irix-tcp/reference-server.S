/* Original IRIX-only echo server for four paired transfer probes. */
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
    li $8, 0x000217df /* family 2, port 6111 */
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
    li $s4, 4
accept:
    move $a0, $s0
    move $a1, $zero
    move $a2, $zero
    checked 1089
    move $s1, $v0
    li $s2, 8
    addiu $s3, $sp, 96
read:
    move $a0, $s1
    move $a1, $s3
    move $a2, $s2
    checked 1003
    blez $v0, failed
    nop
    subu $s2, $s2, $v0
    addu $s3, $s3, $v0
    bnez $s2, read
    nop
    lw $8, 96($sp)
    li $9, 0x58495249
    bne $8, $9, failed
    nop
    lw $8, 100($sp)
    li $9, 0x5f544350
    bne $8, $9, failed
    nop
    li $s2, 8
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
