    .set noreorder
    .section .note.probe,"a",@note
    .long 5,4,0x49524958
    .asciz "Xiri"
    .balign 4
    .long 1
    .text
    .globl _start
_start:
    lw $a0,0($sp)
    addiu $a1,$sp,4
    addiu $sp,$sp,-32
    jal run
     nop
    move $a0,$v0
    li $v0,1001
    syscall
     nop

    .globl trap3
trap3:
    move $v0,$a0
    move $a0,$a1
    move $a1,$a2
    move $a2,$a3
    syscall
     nop
    beqz $a3,1f
     nop
    subu $v0,$zero,$v0
1:  jr $ra
     nop
