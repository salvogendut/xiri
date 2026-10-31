/* Original legacy recvmsg probe; guarded output and an independent queue drain. */
    .set noreorder
    .set noat
    .ifndef OVERFLOW
    .equ OVERFLOW,0
    .endif
    .ifndef READONLY_BASE
    .equ READONLY_BASE,0
    .endif
    .ifndef NAME
    .equ NAME,0
    .endif
    .ifndef READONLY_IOV
    .equ READONLY_IOV,0
    .endif
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
    .macro copy source,dest,count
    la $8,\source
    la $9,\dest
    li $10,\count
1:  lbu $11,0($8)
    sb $11,0($9)
    addiu $8,$8,1
    addiu $9,$9,1
    addiu $10,$10,-1
    bnez $10,1b
    nop
    .endm
    .text
    .globl _start
_start:
    addiu $sp,$sp,-256
    move $s7,$sp
    copy iov_template,iov_space+IOVOFF,136
    copy message_template,message_space+OFFSET,24
    la $s1,message_space+OFFSET
    .ifdef READONLY_MSG
    la $s1,message_template
    .endif
    li $a0,2
    li $a1,2
    move $a2,$zero
    checked 1107
    move $s0,$v0
    move $s5,$s0
    .ifdef RECEIVE_CONNECTED
    move $a0,$s0
    la $a1,address
    li $a2,16
    checked 1091
    move $a0,$s0
    la $a1,hello
    li $a2,8
    checked 1004
    li $8,8
    bne $v0,$8,failed
    nop
    move $a0,$s0
    la $a1,ready
    li $a2,1
    checked 1003
    li $8,1
    bne $v0,$8,failed
    nop
    la $8,ready
    lbu $8,0($8)
    li $9,82
    bne $8,$9,failed
    nop
    .endif
    .if MODE == 2
    move $a0,$s0
    li $a1,4
    li $a2,128
    checked 1062
    .endif
    .ifdef CLOSED
    move $a0,$s0
    checked 1006
    li $s0,-1
    .endif
    move $a0,$s5
    .ifdef FD
    li $a0,FD
    .endif
    move $a1,$s1
    .ifdef POINTER
    li $a1,POINTER
    .endif
    li $a2,FLAGS
    li $v0,1099
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
    la $8,record
    sw $v0,8($8)
    sw $v1,12($8)
    sw $a3,16($8)
    /* Input iov entries must not be modified by the receive operation. */
    la $8,iov_template
    la $9,iov_space+IOVOFF
    li $10,136
    li $s6,1
2:  lbu $11,0($8)
    lbu $12,0($9)
    beq $11,$12,3f
    nop
    move $s6,$zero
3:  addiu $8,$8,1
    addiu $9,$9,1
    addiu $10,$10,-1
    bnez $10,2b
    nop
    la $8,record
    sw $s6,20($8)
    move $8,$s1
    la $9,observed_header
    li $10,24
4:  lbu $11,0($8)
    sb $11,0($9)
    addiu $8,$8,1
    addiu $9,$9,1
    addiu $10,$10,-1
    bnez $10,4b
    nop
    .ifdef RECEIVE_CONNECTED
    .ifndef CLOSED
    .if MODE != 2
    move $s2,$zero
5:  move $a0,$s0
    la $a1,drain_bytes
    addu $a1,$a1,$s2
    li $a2,16
    subu $a2,$a2,$s2
    beqz $a2,failed
    nop
    checked 1003
    beqz $v0,drained
    nop
    addu $s2,$s2,$v0
    b 5b
    nop
drained:
    la $8,drain_count
    sw $s2,0($8)
    .endif
    .endif
    .endif
    bltz $s0,output
    nop
    move $a0,$s0
    checked 1006
output:
    li $a0,1
    la $a1,record
    li $a2,192
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
6:  b 6b
    nop
    .section .rodata
    .balign 4
address: .word 0x000217e3,0x7f000001,0,0
hello: .word CASE,MODE
readonly_data: .ascii "READONLY_DATAxxx"
    .balign 4
iov_template:
    .ifdef BASE
    .word BASE
    .elseif READONLY_BASE
    .word readonly_data
    .else
    .word payload_guard+16
    .endif
    .ifdef TWO
    .word 3
    .ifdef BAD_SECOND
    .word 0
    .else
    .word payload_guard+32
    .endif
    .word 5
    .elseif OVERFLOW
    .word 0x40000000,payload_guard+32,0x40000000
    .else
    .word LENGTH,0,0
    .endif
    .space 120
message_template:
    .ifdef NAMEPTR
    .word NAMEPTR
    .elseif NAME
    .word name_guard+8
    .else
    .word 0
    .endif
    .word NAMELEN
    .ifdef IOVP
    .word IOVP
    .elseif READONLY_IOV
    .word iov_template
    .else
    .word iov_space+IOVOFF
    .endif
    .word IOVCNT
    .ifdef RIGHTSPTR
    .word RIGHTSPTR
    .else
    .word 0
    .endif
    .word RIGHTSLEN
    .data
    .balign 16
record: .word 0x58494431,CASE,0,0,0,0,0,0
payload_guard: .fill 64,1,0xa5
name_guard: .fill 32,1,0xa5
observed_header: .space 24
    .space 8
drain_count: .word 0xffffffff
drain_bytes: .space 16
    .space 12
message_space: .space 32
iov_space: .space 140
ready: .space 4
