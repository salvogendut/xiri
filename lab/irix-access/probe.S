/* Original libc-free access probe. 64-byte BE record, IDs before and after. */
    .set noreorder
    .set noat
    .section .note.probe,"a",@note
    .long 5,4,0x49524958
    .asciz "Xiri"
    .balign 4
    .long 1
    .macro checked n
    li $v0,\n
    syscall
    nop
    bnez $a3,failed
    nop
    .endm
    .text
    .globl _start
_start:
    lw $8,0($sp)
    lw $9,8($sp)
    addiu $sp,$sp,-64
    move $s7,$sp
    li $10,1
    beq $8,$10,identities
    nop
    /* Reference-only identity index. NetBSD uses its native runner. */
    lbu $8,0($9)
    addiu $8,$8,-48
    sltiu $9,$8,6
    beqz $9,failed
    nop
    sll $8,$8,4
    la $s0,ids
    addu $s0,$s0,$8
    /* Original IRIX syssgi SETGROUPS; match the native runner's setup. */
    li $a0,40
    move $a1,$zero
    la $a2,record
    checked 1040
    lw $a0,8($s0)
    lw $a1,12($s0)
    checked 1123
    lw $a0,0($s0)
    lw $a1,4($s0)
    checked 1124
    /* Confirm that setregid/setreuid did not repopulate the group list. */
    li $a0,41
    move $a1,$zero
    la $a2,record
    checked 1040
    bnez $v0,failed
    nop
identities:
    checked 1024
    la $8,record
    sw $v0,24($8)
    sw $v1,28($8)
    checked 1047
    la $8,record
    sw $v0,32($8)
    sw $v1,36($8)
    li $a0,0x00802000
    li $a1,8192
    checked 1135
    .ifdef TAIL
    la $8,path
    li $9,0x00802000-TAIL
    li $10,TAIL
1:  lbu $11,0($8)
    sb $11,0($9)
    addiu $8,$8,1
    addiu $9,$9,1
    addiu $10,$10,-1
    bnez $10,1b
    nop
    .endif
    la $a0,path+PATHOFF
    li $a1,MODE
    .ifdef PATHPTR
    li $a0,PATHPTR
    .endif
    .ifdef TAIL
    li $a0,0x00802000-TAIL
    .endif
    .if INDIRECT
    move $a2,$a1
    move $a1,$a0
    li $a0,1033
    li $v0,1000
    .else
    li $v0,1033
    .endif
    .ifdef BAD_STACK
    li $sp,BAD_STACK
    .endif
    .ifdef N32
    dli $s3,0x1234567887654321
    .endif
    li $v1,0xfeedface
    syscall
    nop
    move $sp,$s7
    la $8,record
    sw $v0,8($8)
    sw $v1,12($8)
    sw $a3,16($8)
    .ifdef N32
    dli $9,0x1234567887654321
    bne $s3,$9,failed
    nop
    .endif
    checked 1024
    la $8,record
    sw $v0,40($8)
    sw $v1,44($8)
    checked 1047
    la $8,record
    sw $v0,48($8)
    sw $v1,52($8)
    li $a0,1
    la $a1,record
    li $a2,64
    checked 1004
    li $8,64
    bne $v0,$8,failed
    nop
    move $a0,$zero
    b finish
    nop
failed:
    li $a0,99
finish:
    li $v0,1001
    syscall
    nop
2:  b 2b
    nop
    .section .rodata
path:
    .include "path.inc"
    .balign 4
ids:
    .word 0,0,0,0
    .word 1234,1234,2345,2345
    .word 1234,0,2345,0
    .word 0,1234,0,2345
    .word 1234,1234,2345,3456
    .word 1234,1234,3456,2345
    .data
    .balign 8
record: .word 0x58494143,CASE,0,0,0,MODE,0,0,0,0,0,0,0,0,0xa5a5a5a5,0x5a5a5a5a
