/* Original SIOCNREAD probe: queue preservation and guarded four-byte output. */
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
    .if KIND == 0
    li $a0,2
    li $a1,2
    move $a2,$zero
    checked 1107
    move $s0,$v0
    .if STATE > 0
    move $a0,$s0
    la $a1,address
    li $a2,16
    checked 1091
    move $a0,$s0
    la $a1,header
    li $a2,8
    checked 1004
    li $8,8
    bne $v0,$8,failed
    nop
    move $a0,$s0
    la $a1,readybuf
    li $a2,1
    checked 1003
    li $8,1
    bne $v0,$8,failed
    nop
    la $8,readybuf
    lbu $8,0($8)
    li $9,82
    bne $8,$9,failed
    nop
    .if STATE >= 2
    /* A MSG_PEEK loop verifies the complete payload before the ioctl.
     * Queue readiness is never inferred from the operation under test. */
    li $s2,10000
peek:
    move $a0,$s0
    la $a1,message
    li $a2,2
    checked 1099
    li $8,17
    beq $v0,$8,queued
    nop
    addiu $s2,$s2,-1
    bnez $s2,peek
    nop
    b failed
    nop
queued:
    .if STATE >= 3
    li $s2,5
    .if STATE == 4
    li $s2,17
    .endif
    la $s1,payload
before_read:
    move $a0,$s0
    move $a1,$s1
    move $a2,$s2
    checked 1003
    blez $v0,failed
    nop
    addu $s1,$s1,$v0
    subu $s2,$s2,$v0
    bnez $s2,before_read
    nop
    .if STATE == 4
    move $a0,$s0
    la $a1,readybuf
    li $a2,1
    checked 1003
    bnez $v0,failed
    nop
    .endif
    .endif
    .endif
    .endif
    .else
    .if KIND == 1
    la $a0,path
    li $a1,OPEN_FLAGS
    move $a2,$zero
    checked 1005
    move $s0,$v0
    .ifdef PRE_READ
    move $a0,$s0
    la $a1,readybuf
    li $a2,5
    checked 1003
    .endif
    .else
    li $s0,FD
    .endif
    .endif
    .ifdef CLOSED
    move $a0,$s0
    checked 1006
    .endif
    .ifdef NONBLOCK
    move $a0,$s0
    li $a1,4
    li $a2,0x80
    checked 1062
    .endif
    move $a0,$s0
    li $a1,COMMAND
    la $a2,outguard+8+ALIGN
    .ifdef BUFPTR
    li $a2,BUFPTR
    .endif
    .ifdef READONLY
    la $a2,readonly
    .endif
    .ifdef TAIL
    li $a2,0x00802000-TAIL
    .endif
    li $v0,1054
    .if INDIRECT
    move $a3,$a2
    move $a2,$a1
    move $a1,$a0
    li $a0,1054
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
    .ifdef REPEAT
    move $a0,$s0
    li $a1,COMMAND
    la $a2,outguard+20
    li $v0,1054
    syscall
    nop
    la $8,record
    sw $v0,44($8)
    sw $a3,48($8)
    .endif
    .ifdef NONBLOCK
    move $a0,$s0
    li $a1,4
    move $a2,$zero
    checked 1062
    .endif
    .if KIND == 0
    .ifndef CLOSED
    .if STATE >= 2
    la $s1,payload
    li $s2,17
    .if STATE == 3
    addiu $s1,$s1,5
    li $s2,12
    .endif
    .if STATE == 4
    li $s2,0
    .endif
    beqz $s2,drained
    nop
after_read:
    move $a0,$s0
    move $a1,$s1
    move $a2,$s2
    checked 1003
    blez $v0,failed
    nop
    addu $s1,$s1,$v0
    subu $s2,$s2,$v0
    bnez $s2,after_read
    nop
drained:
    move $a0,$s0
    la $a1,readybuf
    li $a2,1
    checked 1003
    bnez $v0,failed
    nop
    la $8,record
    li $9,17
    sw $9,40($8)
    .endif
    .endif
    .endif
    .ifndef CLOSED
    .if KIND < 2
    move $a0,$s0
    checked 1006
    .endif
    .endif
    li $8,0x00801fe0
    la $9,tailguard
    li $10,32
2:  lbu $11,0($8)
    sb $11,0($9)
    addiu $8,$8,1
    addiu $9,$9,1
    addiu $10,$10,-1
    bnez $10,2b
    nop
    li $a0,1
    la $a1,record
    li $a2,160
    checked 1004
    li $8,160
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
readonly: .space 32,0xa5
address: .word 0x000217e5,0x7f000001,0,0
header: .word CASE,STATE
    .data
    .balign 8
record: .word 0x58494e52,CASE,0,0,0,1,0,0,0,0,0,0,0,0,0,0
outguard: .space 32,0xa5
tailguard: .space 32,0xa5
payload: .space 32,0xa5
readybuf: .space 32
peekbuf: .space 32
iov: .word peekbuf,17
message: .word 0,0,iov,1,0,0
