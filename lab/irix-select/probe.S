/* Original select probe: explicit 32-bit sets/timeval, guarded snapshots. */
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
    copy set_template,rbuf+8+ROFF,128
    copy set_template,wbuf+8+WOFF,128
    copy set_template,ebuf+8+EOFF,128
    copy time_template,tbuf+8+TOFF,8
    .if SOCKET
    li $a0,2
    li $a1,2
    move $a2,$zero
    checked 1107
    move $s0,$v0
    move $a0,$s0
    la $a1,address
    li $a2,16
    checked 1091
    move $a0,$s0
    la $a1,hello
    li $a2,8
    checked 1004
    move $a0,$s0
    la $a1,ready
    li $a2,1
    checked 1003
    li $8,1
    bne $v0,$8,failed
    nop
    move $a0,$s0
    la $a1,start_byte
    li $a2,1
    checked 1004
    .else
open_file:
    la $a0,filename
    move $a1,$zero
    move $a2,$zero
    checked 1005
    move $s0,$v0
    slti $8,$s0,OPEN_FD
    bnez $8,open_file
    nop
    .endif
    li $8,OPEN_FD
    bne $s0,$8,failed
    nop
    .ifdef CLOSED
    move $a0,$s0
    checked 1006
    .endif
    .macro bit buf,enable,offset
    .if \enable
    li $8,BIT
    srl $9,$8,5
    sll $9,$9,2
    andi $8,$8,31
    li $10,1
    sllv $10,$10,$8
    la $11,\buf+8+\offset
    addu $11,$11,$9
    /* Bytes avoid an unaligned sw in the deliberately unaligned fixtures. */
    srl $12,$10,24
    sb $12,0($11)
    srl $12,$10,16
    sb $12,1($11)
    srl $12,$10,8
    sb $12,2($11)
    sb $10,3($11)
    .endif
    .endm
    bit rbuf,R,ROFF
    bit wbuf,W,WOFF
    bit ebuf,E,EOFF
    .ifdef SECOND_FD
    la $8,rbuf+8
    lw $9,0($8)
    ori $9,$9,8
    sw $9,0($8)
    .endif
    li $a0,ND
    la $a1,rbuf+8+ROFF
    la $a2,wbuf+8+WOFF
    la $a3,ebuf+8+EOFF
    la $s1,tbuf+8+TOFF
    .ifdef RP
    li $a1,RP
    .endif
    .ifdef WP
    li $a2,WP
    .endif
    .ifdef EP
    li $a3,EP
    .endif
    .ifdef TP
    li $s1,TP
    .endif
    .ifdef READONLY_R
    la $a1,readonly_set
    .endif
    .ifdef READONLY_W
    la $a2,readonly_set
    .endif
    .ifdef READONLY_T
    la $s1,time_template
    .endif
    .ifdef ALIAS_RW
    move $a2,$a1
    .endif
    .ifdef ALIAS_RE
    move $a3,$a1
    .endif
    .ifdef N32
    move $8,$s1
    .else
    sw $s1,16($sp)
    .endif
    li $v0,1100
    .if INDIRECT
    .ifdef N32
    move $9,$8
    move $8,$a3
    .else
    sw $a3,16($sp)
    sw $s1,20($sp)
    .endif
    move $a3,$a2
    move $a2,$a1
    move $a1,$a0
    li $a0,1100
    li $v0,1000
    .endif
    .ifdef BAD_STACK
    li $sp,BAD_STACK
    .endif
    li $v1,0xfeedface
    .ifdef N32
    dli $s3,0x1234567887654321
    .endif
    syscall
    nop
    move $sp,$s7
    la $8,record
    sw $v0,8($8)
    sw $v1,12($8)
    sw $a3,16($8)
    .ifdef N32
    dli $8,0x1234567887654321
    bne $s3,$8,failed
    nop
    .endif
    /* Successful delayed-read cases also prove data/EOF after wakeup. */
    .if SOCKET && MODE != 2
    bnez $a3,done
    nop
    li $8,1
    bne $v0,$8,done
    nop
    move $a0,$s0
    la $a1,drain
    li $a2,1
    checked 1003
    la $8,record
    sw $v0,20($8)
    .endif
done:
    li $a0,1
    la $a1,record
    li $a2,512
    checked 1004
    li $8,512
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
filename: .asciz "input.txt"
    .balign 4
address: .word 0x000217e4,0x7f000001,0,0
hello: .word CASE,MODE
start_byte: .ascii "S"
    .balign 4
time_template: .word SEC,USEC
set_template:
    .set pos,0
    .rept 32
    .if pos < ((ND+31)/32) || pos < 2
    .long 0
    .else
    .long 0xa5a5a5a5
    .endif
    .set pos,pos+1
    .endr
readonly_set:
    .long 8
    .space 124,0
    .data
    .balign 8
record:
    .word 0x58495249,CASE,0,0,0,0xffffffff,1,0
rbuf: .space 144,0xa5
wbuf: .space 144,0xa5
ebuf: .space 144,0xa5
tbuf: .space 24,0xa5
drain: .space 24,0xa5
ready: .space 4,0
