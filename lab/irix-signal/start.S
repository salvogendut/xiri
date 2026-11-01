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
    /* Leave readable stack space above the interrupted call for frame capture. */
    addiu $sp,$sp,-4128
    jal main
    nop
    move $a0,$v0
    li $v0,1001
    syscall
    nop
1:  b 1b
    nop
