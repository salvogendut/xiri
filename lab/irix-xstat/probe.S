/* Original xstat probe: guarded output and end-of-mapping copyout snapshot. */
    .set noreorder
    .set noat
    .section .note.probe,"a",@note
    .long 5,4,0x49524958
    .asciz "Xiri"
    .balign 4
    .long 1
    .macro checked number
    li $v0,\number
    syscall
    nop
    bnez $a3,failed
    nop
    .endm
    .text
    .globl _start
_start:
    lw $8,0($sp)
    addiu $sp,$sp,-64
    move $s7,$sp
    li $9,1
    beq $8,$9,identities
    nop
    /* Reference-only argument; NetBSD uses credentials set by its parent. */
    li $a0,1234
    checked 1046
    li $a0,1234
    checked 1023
identities:
    checked 1024
    la $8,record
    sw $v0,24($8)
    sw $v1,28($8)
    checked 1047
    la $8,record
    sw $v0,32($8)
    sw $v1,36($8)
    /* Make the following page inaccessible on either loader. */
    li $a0,0x00802000
    li $a1,8192
    checked 1135
    li $8,0x00801f00
    li $9,256
    li $10,0xa5
1:  sb $10,0($8)
    addiu $8,$8,1
    addiu $9,$9,-1
    bnez $9,1b
    nop
    li $a0,VERSION
    la $a1,path
    la $a2,outguard+8+ALIGN
    .ifdef PATHPTR
    li $a1,PATHPTR
    .endif
    .ifdef BUFPTR
    li $a2,BUFPTR
    .endif
    .ifdef READONLY
    la $a2,readonly
    .endif
    .ifdef TAIL
    li $a2,0x00802000-TAIL
    .endif
    li $v0,1158
    .if INDIRECT
    move $a3,$a2
    move $a2,$a1
    move $a1,$a0
    li $a0,1158
    li $v0,1000
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
    li $8,0x00801f00
    la $9,tailguard
    li $10,256
2:  lbu $11,0($8)
    sb $11,0($9)
    addiu $8,$8,1
    addiu $9,$9,1
    addiu $10,$10,-1
    bnez $10,2b
    nop
    li $a0,1
    la $a1,record
    li $a2,576
    checked 1004
    li $8,576
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
3:  b 3b
    nop
    .section .rodata
path:
    .include "path.inc"
    .balign 4
readonly: .space 256,0xa5
    .data
    .balign 8
record: .word 0x58495354,CASE,0,0,0,1,0,0,0,0,0,0,0,0,0,0
outguard: .space 256,0xa5
tailguard: .space 256,0xa5
