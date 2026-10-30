/* Original static o32 segment fixtures. No libc or vendor code. */
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
    .macro fault_ready
    li $a0, 1
    address $a1, message
    li $a2, 15
    call 1004
    li $t0, 15
    bne $v0, $t0, failed
    nop
    .endm
    .macro call number
    li $v0, \number
    syscall
    nop
    bne $a3, $zero, failed
    nop
    .endm

    .text
    .globl _start
    .ent _start
_start:
    addiu $sp, $sp, -32
    .ifndef PURE_BSS
    /* Check every initialized byte, including both sides of a page edge. */
    address $s0, initialized
    address $s1, initialized_end
    li $t1, 0x5a
check_data:
    lbu $t0, 0($s0)
    bne $t0, $t1, failed
    nop
    addiu $s0, $s0, 1
    bne $s0, $s1, check_data
    nop
    .endif

    /* Check all BSS, including the tail of a file page and whole zero pages. */
    address $s0, zero_start
    address $s1, zero_end
check_zero:
    lbu $t0, 0($s0)
    bne $t0, $zero, failed
    nop
    addiu $s0, $s0, 1
    bne $s0, $s1, check_zero
    nop

    /* Dirty each byte, then read it back; later execs must start pristine. */
    address $s0, zero_start
    li $t1, 0xa7
write_zero:
    sb $t1, 0($s0)
    lbu $t0, 0($s0)
    bne $t0, $t1, failed
    nop
    addiu $s0, $s0, 1
    bne $s0, $s1, write_zero
    nop
    .ifndef PURE_BSS
    address $s0, initialized
    address $s1, initialized_end
write_data:
    sb $t1, 0($s0)
    lbu $t0, 0($s0)
    bne $t0, $t1, failed
    nop
    addiu $s0, $s0, 1
    bne $s0, $s1, write_data
    nop
    .endif

    .ifdef TEXT_WRITE
    fault_ready
    address $t0, _start
    sw $zero, 0($t0)
    b failed
    nop
    .endif
    .ifdef GAP_READ
    fault_ready
    lui $t0, 0x0050
    lw $t1, 0($t0)
    b failed
    nop
    .endif
    .ifdef END_READ
    fault_ready
    address $t0, zero_end
    addiu $t0, $t0, 4095
    li $t1, -4096
    and $t0, $t0, $t1
    lw $t1, 0($t0)
    b failed
    nop
    .endif

    /* Use BSS as a read buffer and as the source of an exact write. */
    address $a0, zero_path
    move $a1, $zero
    move $a2, $zero
    call 1005
    move $s2, $v0
    move $a0, $s2
    address $a1, zero_start
    li $a2, 32
    call 1003
    li $t0, 32
    bne $v0, $t0, failed
    nop
    move $a0, $s2
    call 1006
    address $s0, zero_start
    lw $t0, 0($s0)
    lw $t1, 28($s0)
    or $t0, $t0, $t1
    bne $t0, $zero, failed
    nop
    address $t0, message
    li $t1, 15
copy_message:
    lbu $t2, 0($t0)
    sb $t2, 0($s0)
    addiu $t0, $t0, 1
    addiu $s0, $s0, 1
    addiu $t1, $t1, -1
    bne $t1, $zero, copy_message
    nop
    li $a0, 1
    address $a1, zero_start
    li $a2, 15
    call 1004
    li $t0, 15
    bne $v0, $t0, failed
    nop
    li $a0, 37
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
    .end _start

    .section .rodata
zero_path: .asciz "/dev/zero"
message: .ascii "XIRI_ABI_PROBE\n"

    .ifndef PURE_BSS
    .data
    .balign 16
initialized:
    .ifdef SHORT_BSS
    .fill 32, 1, 0x5a
    .else
    .ifdef ALIGNED_DATA
    .fill 4096, 1, 0x5a
    .else
    .fill 4112, 1, 0x5a
    .endif
    .endif
initialized_end:
    .endif

    .bss
    .balign 16
zero_start:
    .ifdef SHORT_BSS
    .space 64
    .else
    .space 8208
    .endif
zero_end:

    /* Bytes present in the file after data must never appear in BSS. */
    .section .poison,"",@progbits
    .fill 4096, 1, 0xa5
