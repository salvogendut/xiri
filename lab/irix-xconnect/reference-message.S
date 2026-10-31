/* Original IRIX-only peer: fixed records of received bytes and optional EOF ack. */
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
    li $8,0x000217e2
    sw $8,64($sp)
    li $8,0x7f000001
    sw $8,68($sp)
    sw $zero,72($sp)
    sw $zero,76($sp)
    move $a0,$s0
    addiu $a1,$sp,64
    li $a2,16
    checked 1090
    move $a0,$s0
    li $a1,4
    checked 1096
    li $8,0x5244590a
    sw $8,80($sp)
    li $a0,1
    addiu $a1,$sp,80
    li $a2,4
    checked 1004
    li $s4,COUNT
    li $s7,-1
accept:
    move $a0,$s0
    move $a1,$zero
    move $a2,$zero
    checked 1089
    move $s1,$v0
    bltz $s7,new_header
    nop
    move $a0,$s7
    checked 1006
    li $s7,-1
new_header:
    addiu $s3,$sp,80
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
    lw $8,80($sp)
    sw $8,96($sp)
    lw $s5,84($sp)
    sw $zero,104($sp)
    sw $zero,108($sp)
    sw $zero,112($sp)
    sw $zero,116($sp)
    move $s6,$zero
body:
    move $a0,$s1
    addiu $a1,$sp,104
    addu $a1,$a1,$s6
    li $a2,16
    subu $a2,$a2,$s6
    bnez $a2,read
    nop
    addiu $a1,$sp,128
    li $a2,1
read:
    checked 1003
    beqz $v0,received
    nop
    addu $s6,$s6,$v0
    slti $8,$s6,17
    beqz $8,failed
    nop
    b body
    nop
received:
    sw $s6,100($sp)
    beqz $s5,output
    nop
    move $a0,$s1
    addiu $a1,$sp,100
    li $a2,4
    checked 1004
    li $8,4
    bne $v0,$8,failed
    nop
output:
    li $a0,1
    addiu $a1,$sp,96
    li $a2,24
    checked 1004
    li $8,24
    bne $v0,$8,failed
    nop
    beqz $s5,close_client
    nop
    move $s7,$s1
    b next_client
    nop
close_client:
    move $a0,$s1
    checked 1006
next_client:
    addiu $s4,$s4,-1
    bnez $s4,accept
    nop
    bltz $s7,close_listener
    nop
    move $a0,$s7
    checked 1006
close_listener:
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
