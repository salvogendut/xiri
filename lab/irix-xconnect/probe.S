/* Original o32/n32 probes for the next X-client interfaces. */
    .set noreorder
    .set noat
    .section .note.probe,"a",@note
    .long 5,4,0x49524958
    .asciz "Xiri"
    .balign 4
    .long 1
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
    addiu $sp,$sp,-2048
    move $s7,$sp
    li $s0,-1
    move $s6,$zero
    .if KIND == 8
    addiu $8,$sp,64
    li $9,16
    li $10,0xa5a5a5a5
1:  sw $10,0($8)
    addiu $8,$8,4
    addiu $9,$9,-1
    bnez $9,1b
    nop
    addiu $a0,$sp,80+OFFSET
    .ifdef POINTER
    li $a0,POINTER
    .endif
    .ifdef READONLY
    la $a0,payload
    .endif
    li $a1,LENGTH
    move $a2,$zero
    li $v0,1108
    .else
    .ifdef FCHECK
    li $s0,3
    .else
    .ifdef FILE
    la $a0,devnull
    li $a1,FILE
    move $a2,$zero
    checked 1005
    .else
    li $a0,2
    li $a1,2
    move $a2,$zero
    checked 1107
    .endif
    move $s0,$v0
    .endif
    .if KIND == 9
    .ifdef PRESET_FD
    move $a0,$s0
    li $a1,2
    li $a2,PRESET_FD
    checked 1062
    .endif
    .ifdef PRESET_FL
    move $a0,$s0
    li $a1,4
    li $a2,PRESET_FL
    checked 1062
    .endif
    move $a0,$s0
    li $a1,CMD
    li $a2,ARG
    li $v0,1062
    .else
    .ifdef MESSAGE_CONNECTED
    li $8,0x000217e2 /* family 2, loopback port 6114 */
    sw $8,192($sp)
    li $8,0x7f000001
    sw $8,196($sp)
    sw $zero,200($sp)
    sw $zero,204($sp)
    move $a0,$s0
    addiu $a1,$sp,192
    li $a2,16
    checked 1091
    li $8,CASE
    sw $8,208($sp)
    li $8,ACK
    sw $8,212($sp)
    move $a0,$s0
    addiu $a1,$sp,208
    li $a2,8
    checked 1004
    li $8,8
    bne $v0,$8,failed
    nop
    .endif
    .if KIND == 10
    /* Sixteen explicit 32-bit iovec pairs, copied bytewise for alignment tests. */
    addiu $8,$sp,256
    li $9,34
1:  sw $zero,0($8)
    addiu $8,$8,4
    addiu $9,$9,-1
    bnez $9,1b
    nop
    la $8,payload
    .ifdef BASE
    li $8,BASE
    .endif
    sw $8,256($sp)
    li $9,LENGTH
    sw $9,260($sp)
    .ifdef TWO
    li $9,3
    sw $9,260($sp)
    la $8,payload+3
    .ifdef BAD_SECOND
    move $8,$zero
    .endif
    sw $8,264($sp)
    li $9,5
    sw $9,268($sp)
    .endif
    .ifdef OVERFLOW
    li $9,0x40000000
    sw $9,260($sp)
    sw $9,268($sp)
    la $8,payload
    sw $8,264($sp)
    .endif
    addiu $8,$sp,256
    addiu $9,$sp,512+IOVOFF
    li $10,136
2:  lbu $11,0($8)
    sb $11,0($9)
    addiu $8,$8,1
    addiu $9,$9,1
    addiu $10,$10,-1
    bnez $10,2b
    nop
    sw $zero,128($sp)
    sw $zero,132($sp)
    .ifdef NAME
    li $8,1
    sw $8,128($sp)
    li $8,16
    sw $8,132($sp)
    .endif
    addiu $8,$sp,512+IOVOFF
    .ifdef IOVP
    li $8,IOVP
    .endif
    sw $8,136($sp)
    li $8,IOVCNT
    .ifdef TWO
    li $8,2
    .endif
    .ifdef OVERFLOW
    li $8,2
    .endif
    sw $8,140($sp)
    sw $zero,144($sp)
    sw $zero,148($sp)
    .ifdef RIGHTS
    li $8,1
    sw $8,144($sp)
    li $8,4
    sw $8,148($sp)
    .endif
    addiu $8,$sp,128
    addiu $9,$sp,768+OFFSET
    li $10,24
3:  lbu $11,0($8)
    sb $11,0($9)
    addiu $8,$8,1
    addiu $9,$9,1
    addiu $10,$10,-1
    bnez $10,3b
    nop
    move $a0,$s0
    addiu $a1,$sp,768+OFFSET
    .ifdef POINTER
    li $a1,POINTER
    .endif
    .ifdef READONLY
    la $a1,readonly_message
    .endif
    li $a2,FLAGS
    li $v0,1102
    .else /* shutdown */
    .ifdef MESSAGE_CONNECTED
    move $a0,$s0
    la $a1,payload
    li $a2,8
    checked 1004
    li $8,8
    bne $v0,$8,failed
    nop
    .endif
    .ifdef REPEAT
    move $a0,$s0
    li $a1,HOW
    checked 1106
    .endif
    move $a0,$s0
    li $a1,HOW
    move $a2,$zero
    li $v0,1106
    .endif
    .endif
    .ifdef CLOSED
    move $s5,$v0
    move $s4,$a1
    move $s2,$a2
    move $a0,$s0
    checked 1006
    move $a0,$s0
    li $s0,-1
    move $v0,$s5
    move $a1,$s4
    move $a2,$s2
    .endif
    .ifdef FD
    li $a0,FD
    .endif
    .endif
    .if INDIRECT
    move $a3,$a2
    move $a2,$a1
    move $a1,$a0
    move $a0,$v0
    li $v0,1000
    .endif
    .ifdef BAD_STACK
    li $sp,BAD_STACK
    .endif
    li $v1,0xfeedface
    .ifdef N32
    dli $s3,0x1234567887654321
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
    move $sp,$s7
    .ifdef N32
    dli $8,0x1234567887654321
    bne $s3,$8,failed
    nop
    .endif
    sw $v0,40($sp)
    sw $v1,44($sp)
    sw $a3,48($sp)
    .if KIND == 9
    bltz $s0,record
    nop
    move $a0,$s0
    li $a1,3
    .if CMD == 1 || CMD == 2
    li $a1,1
    .endif
    move $a2,$zero
    checked 1062
    move $s6,$v0
    .endif
    .if KIND == 11
    .ifdef MESSAGE_CONNECTED
    bnez $a3,close
    nop
    .if HOW == 1
    /* Peer acknowledges EOF while this process still owns the read half. */
    addiu $s1,$sp,224
    li $s2,4
4:  move $a0,$s0
    move $a1,$s1
    move $a2,$s2
    checked 1003
    blez $v0,failed
    nop
    addu $s1,$s1,$v0
    subu $s2,$s2,$v0
    bnez $s2,4b
    nop
    lw $8,224($sp)
    li $9,8
    bne $8,$9,failed
    nop
    li $s6,1
    .elseif HOW == 0 || HOW == 2
    move $a0,$s0
    addiu $a1,$sp,224
    li $a2,4
    checked 1003
    bnez $v0,failed
    nop
    li $s6,1
    .endif
    .endif
    .endif
close:
    bltz $s0,record
    nop
    move $a0,$s0
    checked 1006
record:
    li $8,0x58494431
    sw $8,32($sp)
    li $8,CASE
    sw $8,36($sp)
    sw $s6,52($sp)
    sw $zero,56($sp)
    sw $zero,60($sp)
    li $a0,1
    addiu $a1,$sp,32
    li $a2,32
    .if KIND == 8
    li $a2,96
    .endif
    checked 1004
    move $a0,$zero
    b finish
    nop
failed:
    li $a0,99
finish:
    li $v0,1001
    syscall
    nop
5:  b 5b
    nop
    .section .rodata
    .balign 4
payload: .ascii "XIRI_MSG"
devnull: .asciz "/dev/null"
    .balign 4
readonly_iov: .word payload,8
readonly_message: .word 0,0,readonly_iov,1,0,0
