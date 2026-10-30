/* Synthetic o32 ABI fixture: no libc, interpreter, global pointer, or TLS. */
    .set noreorder
    .set noat

    .ifdef NATIVE
    .equ SYS_WRITE, 4
    .equ SYS_EXIT, 1
    .section .note.probe,"a",@note
    .long 7, 4, 1
    .asciz "NetBSD"
    .balign 4
    .long 1100000000
    .else
    .equ SYS_WRITE, 1004
    .equ SYS_EXIT, 1001
    .ifdef MARKED
    /* Test-only identity for a future deliberately narrow loader. */
    .section .note.probe,"a",@note
    .long 5, 4, 0x49524958
    .asciz "Xiri"
    .balign 4
    .long 1
    .endif
    .endif

    .text
    .globl _start
    .ent _start
_start:
    addiu $sp, $sp, -32
    addiu $v0, $zero, SYS_WRITE
    addiu $a0, $zero, 1
    lui $a1, %hi(message)
    addiu $a1, $a1, %lo(message)
    addiu $a2, $zero, message_end-message
    syscall
    nop
    bne $a3, $zero, failed
    nop
    addiu $t0, $zero, message_end-message
    bne $v0, $t0, failed
    nop
    addiu $a0, $zero, 37
    b finish
    nop
failed:
    addiu $a0, $zero, 99
finish:
    addiu $v0, $zero, SYS_EXIT
    syscall
    nop
    /* A broken exit implementation must not fall into unrelated memory. */
1:  b 1b
    nop
    .end _start

    .section .rodata
message:
    .ascii "XIRI_ABI_PROBE\n"
message_end:
