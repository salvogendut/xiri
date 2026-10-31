/* Original o32/n32 getsockname probe; 32-byte header + 64 guarded bytes. */
    .set noreorder
    .set noat
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
    move $s7, $sp
    move $s6, $zero
    addiu $8, $sp, 64
    li $9, 16
    li $10, 0xa5a5a5a5
1:  sw $10, 0($8)
    addiu $8, $8, 4
    addiu $9, $9, -1
    bnez $9, 1b
    nop
    addiu $s4, $sp, 80 + NAME_OFFSET
    addiu $s5, $sp, 112 + LEN_OFFSET
    .ifdef OVERLAP
    move $s5, $s4
    .endif
    li $8, LENGTH
    sb $8, 3($s5)
    srl $8, $8, 8
    sb $8, 2($s5)
    srl $8, $8, 8
    sb $8, 1($s5)
    srl $8, $8, 8
    sb $8, 0($s5)
    li $a0, 2
    li $a1, 2
    move $a2, $zero
    checked 1107
    move $s0, $v0
    .ifdef CONNECTED
    li $8, 0x000217e0 /* family 2, loopback port 6112 */
    sw $8, 192($sp)
    li $8, 0x7f000001
    sw $8, 196($sp)
    sw $zero, 200($sp)
    sw $zero, 204($sp)
    move $a0, $s0
    addiu $a1, $sp, 192
    li $a2, 16
    checked 1091
    addiu $s1, $sp, 160
    li $s2, 16
2:  move $a0, $s0
    move $a1, $s1
    move $a2, $s2
    checked 1003
    blez $v0, failed
    nop
    addu $s1, $s1, $v0
    subu $s2, $s2, $v0
    bnez $s2, 2b
    nop
    /* Peer must describe an IPv4 loopback endpoint with a nonzero port. */
    lhu $8, 160($sp)
    li $9, 2
    bne $8, $9, failed
    nop
    lhu $8, 162($sp)
    beqz $8, failed
    nop
    lw $8, 164($sp)
    li $9, 0x7f000001
    bne $8, $9, failed
    nop
    .endif
    .ifdef CLOSED
    move $a0, $s0
    checked 1006
    li $s0, -1
    .endif
    move $a0, $s0
    .ifdef FD
    li $a0, FD
    .endif
    move $a1, $s4
    move $a2, $s5
    .ifdef POINTER
    li $a1, POINTER
    .endif
    .ifdef LEN_POINTER
    li $a2, LEN_POINTER
    .endif
    .ifdef READONLY_NAME
    la $a1, readonly
    .endif
    .ifdef READONLY_LEN
    la $a2, readonly
    .endif
    .if INDIRECT
    move $a3, $a2
    move $a2, $a1
    move $a1, $a0
    li $a0, 1094
    li $v0, 1000
    .else
    li $v0, 1094
    .endif
    .ifdef BAD_STACK
    li $sp, BAD_STACK
    .endif
    li $v1, 0xfeedface
    .ifdef N32
    dli $s3, 0x1234567887654321
    .endif
    .ifdef DELAY
    b observed
    syscall
    b failed
    nop
    .else
    syscall
    nop
    .endif
observed:
    move $sp, $s7
    .ifdef N32
    dli $8, 0x1234567887654321
    bne $s3, $8, failed
    nop
    .endif
    sw $v0, 40($sp)
    sw $v1, 44($sp)
    sw $a3, 48($sp)
    .ifdef CONNECTED
    bnez $a3, failed
    nop
    move $s1, $s4
    addiu $s2, $sp, 160
    /* Compare endpoint fields; padding is checked in the emitted record. */
    li $10, 8
3:  lbu $8, 0($s1)
    lbu $9, 0($s2)
    bne $8, $9, failed
    nop
    addiu $s1, $s1, 1
    addiu $s2, $s2, 1
    addiu $10, $10, -1
    bnez $10, 3b
    nop
    /* Normalize only the independently verified ephemeral port. */
    sb $zero, 2($s4)
    sb $zero, 3($s4)
    li $s6, 1
    .endif
    bltz $s0, record
    nop
    move $a0, $s0
    checked 1006
record:
    li $8, 0x58494431
    sw $8, 32($sp)
    li $8, CASE
    sw $8, 36($sp)
    sw $s6, 52($sp)
    sw $zero, 56($sp)
    sw $zero, 60($sp)
    li $a0, 1
    addiu $a1, $sp, 32
    li $a2, 96
    checked 1004
    li $8, 96
    bne $v0, $8, failed
    nop
    move $a0, $zero
    b finish
    nop
failed:
    li $a0, 99
finish:
    li $v0, 1001
    syscall
    nop
4:  b 4b
    nop
    .section .rodata
    .balign 4
readonly:
    .long 16, 0xa5a5a5a5, 0xa5a5a5a5, 0xa5a5a5a5
