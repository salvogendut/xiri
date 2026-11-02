/* Original static ELF fixture: verify stack alignment, RW data and BSS,
 * then exercise the selected personality without libc or vendor code. */
.set noreorder
.set noat
.text
.globl _start
_start:
    andi $t0,$sp,15
    bnez $t0,failed
    nop
    lui $t0,0x1000
    addiu $t0,$t0,0x4000
    lw $t1,0($t0)
    li $t2,0x12345678
    bne $t1,$t2,failed
    nop
    lw $t1,4($t0)
    bnez $t1,failed
    nop
    sw $t2,4($t0)
    lw $t1,4($t0)
    bne $t1,$t2,failed
    nop
    lui $a1,%hi(message)
    addiu $a1,$a1,%lo(message)
    li $a0,1
    li $a2,message_end-message
    li $v0,SYS_WRITE
    syscall
    nop
    bnez $a3,failed
    nop
    li $t0,message_end-message
    bne $v0,$t0,failed
    nop
    li $a0,37
    b finish
    nop
failed:
    li $a0,99
finish:
    li $v0,SYS_EXIT
    syscall
    nop
1:  b 1b
    nop
message:
    .ascii "XIRI_STATIC_N32\n"
message_end:
