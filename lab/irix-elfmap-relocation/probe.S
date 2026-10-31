/* Original direct SGI_ELFMAP probe for both kernels. No libc/vendor code.
 * The input supplies ELF32 headers and test controls at offset 384.
 * One 48-byte BE record: magic, case, v0/v1/a3, checks, second v0/a3,
 * third v0/a3, preserved data word, reserved. Exit 99 means an assertion. */
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
    .text
    .globl _start
_start:
    lw $t0, 0($sp)
    addiu $sp, $sp, -1024
    li $t1, 1
    beq $t0, $t1, identity_done
    nop
    /* Reference-only setup; NetBSD credentials are set by its native parent. */
    li $a0, 1234
    li $v0, 1046
    syscall
    nop
    bnez $a3, failed
    nop
    li $a0, 1234
    li $v0, 1023
    syscall
    nop
    bnez $a3, failed
    nop
identity_done:
    address $a0, filename
    move $a1, $zero
    li $v0, 1005
    syscall
    nop
    bnez $a3, failed
    nop
    move $s0, $v0
    move $a0, $s0
    addiu $a1, $sp, 32
    li $a2, 512
    li $v0, 1003
    syscall
    nop
    bnez $a3, failed
    nop
    li $t0, 512
    bne $v0, $t0, failed
    nop
    addiu $s1, $sp, 84 /* ELF phoff 52, input buffer at sp+32 */
    lw $s2, 420($sp)  /* action */
    addiu $t0, $sp, 576
    addiu $t1, $sp, 624
1:  sw $zero, 0($t0)
    addiu $t0, $t0, 4
    bne $t0, $t1, 1b
    nop
    li $t0, 0x58494531
    sw $t0, 576($sp)
    lw $t0, 416($sp)
    sw $t0, 580($sp)
    /* Optional /dev/zero occupants before mapping. Preserve sentinels. */
    lw $a0, 436($sp)
    jal occupy
    nop
    sw $v0, 800($sp)
    lw $a0, 440($sp)
    jal occupy
    nop
    sw $v0, 804($sp)
    lw $t0, 432($sp) /* descriptor control */
    beqz $t0, call_primary
    nop
    li $t1, 1
    beq $t0, $t1, bad_fd
    nop
    move $a0, $s0
    li $v0, 1006
    syscall
    nop
    bnez $a3, failed
    nop
    li $t1, 2
    beq $t0, $t1, call_primary /* closed descriptor */
    nop
    address $a0, filename
    li $a1, 1 /* write-only */
    li $t1, 3
    beq $t0, $t1, reopen
    nop
    li $a1, 2 /* read/write */
    li $t1, 6
    beq $t0, $t1, reopen
    nop
    address $a0, dirname
    move $a1, $zero
    li $t1, 4
    beq $t0, $t1, reopen
    nop
    address $a0, zeroname
reopen:
    li $v0, 1005
    syscall
    nop
    bnez $a3, failed
    nop
    move $s0, $v0
    b call_primary
    nop
bad_fd:
    li $s0, -1
call_primary:
    jal save_headers
    nop
    li $a0, 68
    move $a1, $s0
    move $a2, $s1
    lw $a3, 424($sp) /* count */
    lw $t0, 428($sp) /* header pointer control */
    beqz $t0, pointer_done
    nop
    li $a2, 1
    li $t1, 1
    beq $t0, $t1, pointer_done
    nop
    move $a2, $zero
pointer_done:
    li $v1, 0xfeedface
    li $v0, 1040
    syscall
    nop
    sw $v0, 584($sp)
    sw $v1, 588($sp)
    sw $a3, 592($sp)
    jal check_headers
    nop
    bnez $a3, done
    nop
    beqz $s2, done
    nop
    move $s3, $v0
    lw $t0, 8($s1)
    subu $t0, $s3, $t0
    lw $s4, 40($s1)
    addu $s4, $s4, $t0
    jal validate
    nop
    li $t0, 7
    beq $s2, $t0, compete
    nop
    li $t0, 2
    beq $s2, $t0, repeat
    nop
    li $t0, 5
    beq $s2, $t0, rollback
    nop
    li $t0, 6
    beq $s2, $t0, rollback
    nop
    b done
    nop
repeat:
    li $t0, 0x12345678
    sw $t0, 0($s4)
    lw $t1, 16+32($s1)
    addu $t1, $t1, $s4
    sb $t0, 0($t1)
    move $a0, $s3
    lw $a1, 20($s1)
    li $v0, 1135
    syscall
    nop
    bnez $a3, failed
    nop
    move $a0, $s4
    lw $a1, 52($s1)
    li $v0, 1135
    syscall
    nop
    bnez $a3, failed
    nop
    jal map_again
    nop
    sw $v0, 600($sp)
    sw $a3, 604($sp)
    bnez $a3, failed
    nop
    bne $v0, $s3, failed
    nop
    jal validate
    nop
    li $t0, 3
    sw $t0, 596($sp)
    b done
    nop
rollback:
    move $s7, $s4
    li $t0, 0x12345678
    sw $t0, 0($s7)
    lw $t0, 8($s1)
    li $t1, 0x10000
    addu $t0, $t0, $t1
    sw $t0, 8($s1) /* new RX, existing RW: failure after RX mapping */
    li $t0, 6
    bne $s2, $t0, collision_ready
    nop
    lw $t0, 40($s1)
    addiu $t0, $t0, -0x4000
    sw $t0, 40($s1)
    li $t0, 0x8000 /* BSS collides after RX, RW pages, and RW tail */
    sw $t0, 52($s1)
collision_ready:
    jal map_again
    nop
    sw $v0, 600($sp)
    sw $a3, 604($sp)
    move $s6, $a3
    move $s3, $v0
    lw $t0, 0($s7)
    sw $t0, 616($sp)
    li $t1, 0x12345678
    bne $t0, $t1, failed
    nop
    bnez $s6, retry_after_collision
    nop
    /* Original IRIX can relocate: verify the new mappings and old sentinel. */
    lw $t0, 8($s1)
    lw $s4, 40($s1)
    subu $s4, $s4, $t0
    addu $s4, $s4, $s3
    jal validate
    nop
    li $t0, 3
    sw $t0, 596($sp)
    b done
    nop
retry_after_collision:
    li $t0, 6
    bne $s2, $t0, retry_move_data
    nop
    li $t0, 0x2000 /* same RX/RW pages, shorter BSS: all must be free */
    sw $t0, 52($s1)
    b retry_ready
    nop
retry_move_data:
    lw $t0, 40($s1)
    li $t1, 0x10000
    addu $t0, $t0, $t1
    sw $t0, 40($s1)
retry_ready:
    jal map_again
    nop
    sw $v0, 608($sp)
    sw $a3, 612($sp)
    bnez $a3, failed
    nop
    lw $t0, 8($s1)
    bne $v0, $t0, failed
    nop
    move $s3, $v0
    lw $s4, 40($s1)
    jal validate
    nop
    li $t0, 7
    sw $t0, 596($sp)
    b done
    nop
compete:
    /* Keep both prior groups mapped and request a third competing layout. */
    li $t0, 0x12345678
    sw $t0, 0($s4)
    move $s7, $s4
    jal map_again
    nop
    sw $v0, 600($sp)
    sw $a3, 604($sp)
    bnez $a3, failed
    nop
    bne $v0, $s3, 10f
    nop
    b failed
    nop
10: move $s3, $v0
    lw $t0, 8($s1)
    lw $s4, 40($s1)
    subu $s4, $s4, $t0
    addu $s4, $s4, $s3
    jal validate
    nop
    li $t0, 0x12345678
    sw $t0, 0($s4)
    sw $s4, 808($sp)
    jal map_again
    nop
    sw $v0, 608($sp)
    sw $a3, 612($sp)
    bnez $a3, failed
    nop
    beq $v0, $s3, failed
    nop
    move $s3, $v0
    lw $t0, 8($s1)
    lw $s4, 40($s1)
    subu $s4, $s4, $t0
    addu $s4, $s4, $s3
    jal validate
    nop
    lw $t0, 0($s7)
    li $t1, 0x12345678
    bne $t0, $t1, failed
    nop
    lw $t0, 808($sp)
    lw $t0, 0($t0)
    bne $t0, $t1, failed
    nop
    sw $t0, 616($sp)
    li $t0, 3
    sw $t0, 596($sp)
    b done
    nop
map_again:
    sw $ra, 812($sp)
    jal save_headers
    nop
    li $a0, 68
    move $a1, $s0
    move $a2, $s1
    li $a3, 2
    li $v0, 1040
    syscall
    nop
    jal check_headers
    nop
    lw $ra, 812($sp)
    jr $ra
    nop
save_headers:
    move $t0, $s1
    addiu $t1, $sp, 704
    addiu $t2, $t1, 64
11: lw $t3, 0($t0)
    sw $t3, 0($t1)
    addiu $t0, $t0, 4
    addiu $t1, $t1, 4
    bne $t1, $t2, 11b
    nop
    jr $ra
    nop
check_headers:
    move $t0, $s1
    addiu $t1, $sp, 704
    addiu $t2, $t1, 64
12: lw $t3, 0($t0)
    lw $t9, 0($t1)
    bne $t3, $t9, failed
    nop
    addiu $t0, $t0, 4
    addiu $t1, $t1, 4
    bne $t1, $t2, 12b
    nop
    jr $ra
    nop
occupy:
    beqz $a0, 14f
    move $v0, $zero
    sw $a0, 816($sp)
    address $a0, zeroname
    li $a1, 0
    li $v0, 1005
    syscall
    nop
    bnez $a3, failed
    nop
    sw $v0, 16($sp)
    sw $zero, 20($sp)
    .if N32
    move $8, $v0
    move $9, $zero
    .endif
    lw $a0, 816($sp)
    lw $a1, 444($sp)
    li $a2, 3
    li $a3, 2
    li $v0, 1134
    syscall
    nop
    bnez $a3, failed
    nop
    lw $t0, 816($sp)
    bne $t0, $v0, failed
    nop
    li $t0, 0x5a17c0de
    sw $t0, 0($v0)
14: jr $ra
    nop
validate:
    sw $ra, 640($sp)
    addiu $t9, $s3, 256
    jalr $t9
    nop
    li $t0, 0x13572468
    bne $v0, $t0, failed
    nop
    move $t0, $s4
    lw $t1, 48($s1)
    addu $t1, $t1, $s4
    li $t2, 0x3c
2:  beq $t0, $t1, check_bss
    nop
    lbu $t3, 0($t0)
    bne $t3, $t2, failed
    nop
    b 2b
    addiu $t0, $t0, 1
check_bss:
    lw $t1, 52($s1)
    addu $t1, $t1, $s4
3:  beq $t0, $t1, validated
    nop
    lbu $t3, 0($t0)
    bnez $t3, failed
    nop
    b 3b
    addiu $t0, $t0, 1
validated:
    /* Check common displacement against both ELF alignment constraints. */
    lw $t0, 8($s1)
    subu $t0, $s3, $t0
    lw $t1, 28($s1)
    addiu $t1, $t1, -1
    and $t2, $t0, $t1
    sw $t2, 620($sp)
    lw $t1, 60($s1)
    addiu $t1, $t1, -1
    and $t2, $t0, $t1
    lw $t1, 620($sp)
    or $t1, $t1, $t2
    sw $t1, 620($sp)
    li $t0, 1
    sw $t0, 596($sp)
    lw $ra, 640($sp)
    jr $ra
    nop
failed:
    li $s5, 99
    b emit
    nop
done:
    lw $t0, 800($sp)
    beqz $t0, 15f
    nop
    lw $t1, 0($t0)
    li $t2, 0x5a17c0de
    bne $t1, $t2, failed
    nop
15: lw $t0, 804($sp)
    beqz $t0, 16f
    nop
    lw $t1, 0($t0)
    li $t2, 0x5a17c0de
    bne $t1, $t2, failed
    nop
16: move $s5, $zero
emit:
    li $a0, 1
    addiu $a1, $sp, 576
    li $a2, 48
    li $v0, 1004
    syscall
    nop
    bnez $a3, exit_bad
    nop
    li $t0, 48
    bne $v0, $t0, exit_bad
    nop
    bnez $s5, exit_probe
    nop
    lw $t0, 592($sp)
    bnez $t0, exit_probe
    nop
    li $t0, 3
    beq $s2, $t0, text_fault
    nop
    li $t0, 4
    beq $s2, $t0, gap_fault
    nop
    b exit_probe
    nop
text_fault:
    sw $zero, 256($s3)
    b exit_bad
    nop
gap_fault:
    li $t0, 0x10000
    addu $t0, $t0, $s3
    lw $zero, 0($t0)
exit_bad:
    li $s5, 99
exit_probe:
    move $a0, $s5
    li $v0, 1001
    syscall
    nop
4:  b 4b
    nop
    .section .rodata
filename: .asciz "elfmap-input"
dirname: .asciz "."
zeroname: .asciz "/dev/zero"
