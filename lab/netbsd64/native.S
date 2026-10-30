/* Original native NetBSD n32/n64 probes; no libc or IRIX personality. */
    .set noreorder
    .set noat
    .set fp=64
    .section .note.probe,"a",@note
    .long 7, 4, 1
    .asciz "NetBSD"
    .balign 4
    .long 1100000000

    .macro address reg, label
    lui \reg, %hi(\label)
    daddiu \reg, \reg, %lo(\label)
    .endm
    .macro call number
    li $v0, \number
    syscall
    nop
    bnez $a3, failed
    nop
    .endm
    .macro equal reg, constant
    dli $12, \constant
    bne \reg, $12, failed
    nop
    .endm
    .macro map_input
    move $a0, $zero
    li $a1, PAGE_BYTES
    li $a2, 3
    li $a3, 2
    move $8, $s0
    move $9, $zero
    li $10, PAGE_BYTES
    .ifdef INDIRECT
    /* Eight registers: selector, addr, len, prot, flags, fd, pad, offset. */
    move $11, $10
    move $10, $9
    move $9, $8
    move $8, $a3
    move $a3, $a2
    move $a2, $a1
    move $a1, $a0
    li $a0, 197
    call 0
    .else
    call 197
    .endif
    .endm

    .text
    .globl _start
_start:
    daddiu $sp, $sp, -128
    .ifdef REGISTERS
    dli $s0, 0x1234567887654321
    dli $s1, 0x1122334455667788
    daddu $s2, $s0, $s1
    li $s3, 128
1:  call 20
    blez $v0, failed
    nop
    equal $s0, 0x1234567887654321
    equal $s1, 0x1122334455667788
    equal $s2, 0x235689bcdccbbaa9
    addiu $s3, $s3, -1
    bnez $s3, 1b
    nop
    .endif
    .ifdef FP
    dli $12, 0x3ff0000000000000
    dmtc1 $12, $f0
    dli $12, 0x4000000000000000
    dmtc1 $12, $f1
    nop
    add.d $f3, $f0, $f1
    nop
    dmfc1 $s0, $f3
    equal $s0, 0x4008000000000000
    call 20
    dmfc1 $s0, $f1
    equal $s0, 0x4000000000000000
    dmfc1 $s0, $f3
    equal $s0, 0x4008000000000000
    .endif
    .ifdef FILE
    address $a0, path
    move $a1, $zero
    move $a2, $zero
    call 5
    move $s0, $v0
    .endif
    .ifdef SEEK
    move $a0, $s0
    move $a1, $zero
    dli $a2, 0x100001234
    move $a3, $zero
    call 199
    equal $v0, 0x100001234
    move $a0, $s0
    move $a1, $sp
    li $a2, 1
    call 3
    bnez $v0, failed
    nop
    move $a0, $s0
    move $a1, $zero
    li $a2, PAGE_BYTES
    move $a3, $zero
    call 199
    equal $v0, PAGE_BYTES
    move $a0, $s0
    move $a1, $sp
    li $a2, 1
    call 3
    equal $v0, 1
    lbu $s1, 0($sp)
    equal $s1, 0x22
    .endif
    .ifdef MMAP
    map_input
    move $s1, $v0
    andi $12, $s1, PAGE_BYTES-1
    bnez $12, failed
    nop
    lbu $s2, 0($s1)
    equal $s2, 0x22
    li $12, 0x44
    sb $12, 0($s1)
    move $a0, $s1
    li $a1, PAGE_BYTES
    call 73
    map_input
    move $s1, $v0
    lbu $s2, 0($s1)
    equal $s2, 0x22
    move $a0, $s1
    li $a1, PAGE_BYTES
    call 73
    .endif
    .ifdef FILE
    move $a0, $s0
    call 6
    .endif
    .ifdef ERRORS
    li $a0, 1
    move $a1, $zero
    li $a2, 1
    li $v0, 4
    syscall
    nop
    beqz $a3, failed
    nop
    equal $v0, 14
    li $a0, -1
    li $v0, 6
    syscall
    nop
    beqz $a3, failed
    nop
    equal $v0, 9
    .endif
    .ifdef DELAY
    li $v0, 20
    b after_delay
    syscall
    b failed
    nop
after_delay:
    bnez $a3, failed
    nop
    blez $v0, failed
    nop
    .endif
    .ifdef TEXT_FAULT
    address $12, _start
    sw $zero, 0($12)
    b failed
    nop
    .endif
    li $a0, 1
    address $a1, message
    li $a2, message_end-message
    call 4
    equal $v0, message_end-message
    li $a0, 37
    b finish
    nop
failed:
    li $a0, 99
finish:
    li $v0, 1
    syscall
    nop
2:  b 2b
    nop
    .section .rodata
path: .asciz "map-input.bin"
message: .ascii "XIRI_NATIVE64_OK\n"
message_end:
