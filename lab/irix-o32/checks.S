/* Synthetic checks for the opt-in write/exit personality. */
    .set noreorder
    .set noat
    .section .note.probe,"a",@note
    .long 5, 4, 0x49524958
    .asciz "Xiri"
    .balign 4
    .long 1

    .macro expect_error number, expected
    li $v0, \number
    syscall
    nop
    beq $a3, $zero, failed
    nop
    li $t0, \expected
    bne $v0, $t0, failed
    nop
    .endm

    .text
    .globl _start
    .ent _start
_start:
    addiu $sp, $sp, -32
    .ifdef LOOP
1:  b 1b
    nop
    .else
    .ifdef FAULT
    /* No caught signal handlers: an ordinary fault must terminate us. */
    lw $t0, 0($zero)
    nop
    b failed
    nop
    .else
    .ifdef ERRORS
    li $a0, -1
    li $a1, 0
    li $a2, 1
    expect_error 1004, 9
    li $a0, 1
    expect_error 1004, 14
    /* Zero-length write succeeds even with an inaccessible pointer. */
    li $a0, 1
    li $a1, 0
    li $a2, 0
    li $v0, 1004
    syscall
    nop
    bne $a3, $zero, failed
    nop
    bne $v0, $zero, failed
    nop
    .endif
    .ifdef NUMBERS
    /* The historical kernels reject syscall(); the dispatch revision
     * accepts it, so exercise a nested unsupported selector there. */
    .ifdef DISPATCH
    li $a0, 1000
    .else
    li $a0, 1001
    .endif
    expect_error 0, 89
    expect_error 1, 89
    expect_error 999, 89
    expect_error 1000, 89
    expect_error 1002, 89
    expect_error 1198, 89
    expect_error 1255, 89
    expect_error 1256, 89
    expect_error 0x7fffffff, 89
    expect_error 0xffffffff, 89
    .endif
    .ifdef DELAY
    /* A successful write in a taken branch delay slot must resume at target. */
    li $a0, 1
    lui $a1, %hi(message)
    addiu $a1, $a1, %lo(message)
    li $a2, message_end-message
    li $v0, 1004
    b after_delay
    syscall
    b failed
    nop
after_delay:
    bne $a3, $zero, failed
    nop
    li $t0, message_end-message
    bne $v0, $t0, failed
    nop
    .endif
    li $a0, 37
    b finish
    nop
    .endif
    .endif
failed:
    li $a0, 99
finish:
    li $v0, 1001
    syscall
    nop
2:  b 2b
    nop
    .end _start
    .section .rodata
message:
    .ascii "XIRI_ABI_PROBE\n"
message_end:
