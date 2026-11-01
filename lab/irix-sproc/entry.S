/* Capture the raw kernel entry, before a C prologue changes any registers. */
.set noreorder
.text
.globl child_entry
.ent child_entry
child_entry:
    lui $t0,%hi(entry_regs)
    addiu $t0,$t0,%lo(entry_regs)
    sw $a0,0($t0)
    sw $a1,4($t0)
    sw $a2,8($t0)
    sw $a3,12($t0)
    sw $v0,16($t0)
    sw $v1,20($t0)
    sw $sp,24($t0)
    sw $ra,28($t0)
    sw $s0,32($t0)
    sw $s1,36($t0)
    sw $s2,40($t0)
    sw $s3,44($t0)
    addiu $sp,$sp,-32
    jal child_main
    nop
    move $a0,$v0
    li $v0,1001
    syscall
    nop
1:  b 1b
    nop
.end child_entry
