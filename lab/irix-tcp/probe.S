/* Original paired o32/n32 TCP probes. No libc or vendor code. */
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
    li $s0, -1
    move $s6, $zero
    /* Foreign sockaddr_in: uint16 family, network-order port/address. */
    li $12, (FAMILY << 16) | PORT
    sw $12, 96($sp)
    li $12, 0x7f000001
    sw $12, 100($sp)
    sw $zero, 104($sp)
    sw $zero, 108($sp)
    li $12, VALUE
    sw $12, 112($sp)
    .if KIND == 1 || KIND == 2 || KIND == 4
    .ifdef BORROW
    li $s0, 3
    .else
    li $a0, 2
    li $a1, 2
    move $a2, $zero
    checked 1107
    move $s0, $v0
    .endif
    .endif
    .if KIND == 0
    li $a0, DOMAIN
    li $a1, TYPE
    li $a2, PROTOCOL
    .elseif KIND == 1 || KIND == 4
    move $a0, $s0
    addiu $a1, $sp, 96
    li $a2, LENGTH
    .elseif KIND == 2
    move $a0, $s0
    li $a1, LEVEL
    li $a2, OPTION
    addiu $a3, $sp, 112
    li $12, LENGTH
    sw $12, 16($sp)
    .ifdef N32
    move $8, $12
    .endif
    .elseif KIND == 3
    li $a0, TICKS
    .elseif KIND == 5
    li $a0, 22
    li $a1, 3
    move $a2, $zero
    move $a3, $zero
    .endif
    .ifdef FD
    li $a0, FD
    .endif
    .ifdef POINTER
    .if KIND == 2
    li $a3, POINTER
    .else
    li $a1, POINTER
    .endif
    .endif
    .if INDIRECT
    .ifdef N32
    move $9, $8
    move $8, $a3
    .else
    lw $12, 16($sp)
    sw $12, 20($sp)
    sw $a3, 16($sp)
    .endif
    move $a3, $a2
    move $a2, $a1
    move $a1, $a0
    li $a0, TRAP
    li $v0, 1000
    .else
    li $v0, TRAP
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
    dli $12, 0x1234567887654321
    bne $s3, $12, failed
    nop
    .endif
    sw $v0, 40($sp)
    sw $v1, 44($sp)
    sw $a3, 48($sp)
    bnez $a3, emit
    nop
    .if KIND == 0
    move $s0, $v0
    .endif
    .if KIND == 4
    /* Complete eight-byte echo; TCP may split reads/writes. */
    li $12, 0x58495249
    sw $12, 120($sp)
    li $12, 0x5f544350
    sw $12, 124($sp)
    addiu $s1, $sp, 120
    li $s2, 8
1:  move $a0, $s0
    move $a1, $s1
    move $a2, $s2
    checked 1004
    blez $v0, failed
    nop
    subu $s2, $s2, $v0
    addu $s1, $s1, $v0
    bnez $s2, 1b
    nop
    addiu $s1, $sp, 128
    li $s2, 8
2:  move $a0, $s0
    move $a1, $s1
    move $a2, $s2
    checked 1003
    blez $v0, failed
    nop
    subu $s2, $s2, $v0
    addu $s1, $s1, $v0
    bnez $s2, 2b
    nop
    lw $12, 120($sp)
    lw $13, 128($sp)
    bne $12, $13, failed
    nop
    lw $12, 124($sp)
    lw $13, 132($sp)
    bne $12, $13, failed
    nop
    li $s6, 1
    .endif
emit:
    bltz $s0, record
    nop
    move $a0, $s0
    checked 1006
record:
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
    checked 1004
    li $12, 32
    bne $v0, $12, failed
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
3:  b 3b
    nop
