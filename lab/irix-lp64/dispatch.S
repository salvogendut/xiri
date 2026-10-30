/* Original o32/n32 LP64 dispatcher/mapping probes; no libc or vendor code.
 * Each process emits eight big-endian words, then exits. CASE/TRAP/INDIRECT
 * and the feature symbols are supplied by build-irix-lp64.py. */
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
    move $s5, $zero
    move $s4, $zero
    li $a0, ARG0
    li $a1, ARG1
    li $a2, ARG2
    li $a3, ARG3
    sw $zero, 16($sp)
    sw $zero, 20($sp)
    sw $zero, 24($sp)
    .ifdef N32
    move $8, $zero
    move $9, $zero
    move $10, $zero
    .endif

    .ifdef FILE_MAP
    address $a0, input_path
    li $a1, 0
    li $a2, 0
    checked 1005
    move $s0, $v0
    .endif
    .ifdef ZERO_MAP
    address $a0, zero_path
    li $a1, 0
    li $a2, 0
    checked 1005
    move $s0, $v0
    .endif
    .ifdef OPEN_READ
    address $a0, input_path
    li $a1, 0
    li $a2, 0
    .endif
    .ifdef MAPPING
    li $a0, HINT
    li $a1, PAGE_BYTES
    li $a2, 3
    li $a3, 2
    sw $s0, 16($sp)
    li $12, OFFSET
    sw $12, 20($sp)
    .ifdef N32
    move $8, $s0
    move $9, $12
    .endif
    .endif
    .ifdef OCCUPIED
    checked 1134
    move $s5, $v0
    li $12, 0x12345678
    sw $12, 0($s5)
    move $a0, $s5
    li $a1, PAGE_BYTES
    li $a2, 3
    li $a3, 2
    .endif
    .ifdef GUARD
    li $a0, 0
    li $a1, 2*PAGE_BYTES
    li $a2, 3
    li $a3, 2
    sw $s0, 16($sp)
    sw $zero, 20($sp)
    checked 1134
    move $s4, $v0
    addiu $a0, $s4, PAGE_BYTES
    li $a1, PAGE_BYTES
    checked 1135
    /* Indirect mmap needs three spill words: the third is inaccessible. */
    addiu $sp, $s4, PAGE_BYTES-24
    li $12, 2
    sw $12, 16($sp)
    sw $s0, 20($sp)
    li $a0, 1134
    li $a1, 0
    li $a2, PAGE_BYTES
    li $a3, 3
    .endif
    .ifdef FOUR_ARGS
    /* count=0 in the fourth syssgi argument must reach SGI_ELFMAP. */
    li $a0, 68
    li $a1, -1
    li $a2, 0
    li $a3, 0
    .endif
    .ifdef BAD_MMAP
    li $8, -1
    move $9, $zero
    .endif
    .if INDIRECT
    .ifdef N32
    move $10, $9
    move $9, $8
    move $8, $a3
    .else
    /* Shift the six direct o32 slots right by one, preserving home slots. */
    lw $12, 20($sp)
    sw $12, 24($sp)
    lw $12, 16($sp)
    sw $12, 20($sp)
    sw $a3, 16($sp)
    .endif
    move $a3, $a2
    move $a2, $a1
    move $a1, $a0
    li $a0, TRAP
    .endif
    .ifdef BAD_STACK
    li $sp, BAD_STACK
    .endif
    .ifdef N32
    dli $s3, 0x1234567887654321
    .endif
    li $v1, 0xfeedface
    .if INDIRECT
    li $v0, 1000
    .else
    li $v0, TRAP
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
    .ifdef MAPPING
    move $s1, $v0
    andi $12, $s1, 4095
    bnez $12, failed
    nop
    sltiu $12, $s1, PAGE_BYTES
    bnez $12, failed
    nop
    bltz $s1, failed
    nop
    lbu $12, 0($s1)
    li $13, BYTE
    bne $12, $13, failed
    nop
    li $s6, 1
    .ifdef OCCUPIED
    beq $s1, $s5, failed
    nop
    lw $12, 0($s5)
    li $13, 0x12345678
    bne $12, $13, failed
    nop
    li $s6, 3
    .endif
    .ifdef TEXT_HINT
    /* The occupied RX probe must still contain its original instruction. */
    address $12, _start
    lw $s5, 0($12)
    li $13, 0x27bdff00
    bne $s5, $13, failed
    nop
    li $s6, 3
    .endif
    .ifdef FILE_MAP
    li $12, 0x5a
    sb $12, 0($s1)
    move $a0, $s1
    li $a1, PAGE_BYTES
    checked 1135
    move $a0, $zero
    li $a1, PAGE_BYTES
    li $a2, 1
    li $a3, 2
    sw $s0, 16($sp)
    li $12, OFFSET
    sw $12, 20($sp)
    .ifdef N32
    move $8, $s0
    move $9, $12
    .endif
    checked 1134
    lbu $12, 0($v0)
    li $13, BYTE
    bne $12, $13, failed
    nop
    ori $s6, $s6, 4
    .endif
    .endif
    .ifdef OPEN_READ
    move $s0, $v0
    /* Also exercise indirect read and close with real file state. */
    li $a0, 1003
    move $a1, $s0
    addiu $a2, $sp, 96
    li $a3, 1
    checked 1000
    li $12, 1
    bne $v0, $12, failed
    nop
    lbu $12, 96($sp)
    li $13, 0x11
    bne $12, $13, failed
    nop
    li $a0, 1006
    move $a1, $s0
    checked 1000
    li $s6, 1
    .endif
emit:
    li $12, 0x58494431
    sw $12, 32($sp)
    li $12, CASE
    sw $12, 36($sp)
    sw $s6, 52($sp)
    sw $s5, 56($sp)
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
1:  b 1b
    nop
    .section .rodata
zero_path: .asciz "/dev/zero"
input_path: .asciz "dispatch-input"
