/* Original IRIX-only peer: send readiness/data, half-close, observe client close. */
    .set noreorder
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
    addiu $sp,$sp,-256
    li $a0,2
    li $a1,2
    move $a2,$zero
    checked 1107
    move $s0,$v0
    move $a0,$s0
    la $a1,address
    li $a2,16
    checked 1090
    move $a0,$s0
    li $a1,4
    checked 1096
    li $a0,1
    la $a1,ready
    li $a2,4
    checked 1004
    li $s4,COUNT
accept:
    move $a0,$s0
    move $a1,$zero
    move $a2,$zero
    checked 1089
    move $s1,$v0
    addiu $s3,$sp,64
    li $s2,8
header:
    move $a0,$s1
    move $a1,$s3
    move $a2,$s2
    checked 1003
    blez $v0,failed
    nop
    addu $s3,$s3,$v0
    subu $s2,$s2,$v0
    bnez $s2,header
    nop
    lw $s5,68($sp)
    sltiu $8,$s5,3
    beqz $8,failed
    nop
    li $s6,1
    bnez $s5,send
    nop
    li $s6,9
send:
    move $a0,$s1
    la $a1,payload
    move $a2,$s6
    checked 1004
    bne $v0,$s6,failed
    nop
    li $8,2
    beq $s5,$8,wait_close
    nop
    move $a0,$s1
    li $a1,1
    checked 1106
wait_close:
    move $a0,$s1
    addiu $a1,$sp,80
    li $a2,1
    li $v0,1003
    syscall
    nop
    beqz $a3,eof
    nop
    li $8,131 /* IRIX ECONNRESET: closing a socket with unread data. */
    bne $v0,$8,failed
    nop
    b closed
    nop
eof:
    bnez $v0,failed
    nop
closed:
    move $a0,$s1
    checked 1006
    addiu $8,$s6,-1
    sw $8,72($sp)
    li $a0,1
    addiu $a1,$sp,64
    li $a2,12
    checked 1004
    li $8,12
    bne $v0,$8,failed
    nop
    addiu $s4,$s4,-1
    bnez $s4,accept
    nop
    move $a0,$s0
    checked 1006
    move $a0,$zero
    b finish
    nop
failed:
    li $a0,99
finish:
    li $v0,1001
    syscall
    nop
1:  b 1b
    nop
    .section .rodata
    .balign 4
address: .word 0x000217e3,0x7f000001,0,0
ready: .ascii "RDY\n"
payload: .ascii "RXIRI_RCV"
