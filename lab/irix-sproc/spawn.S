/* Raw sproc bridge: fixed callee-saved sentinels expose child register inheritance. */
.set noreorder
.text
.globl spawn_call
.ent spawn_call
spawn_call:
    addiu $sp,$sp,-64
#if N32
    sd $s0,32($sp)
    sd $s1,40($sp)
    sd $s2,48($sp)
    sd $s3,56($sp)
#else
    sw $s0,32($sp)
    sw $s1,36($sp)
    sw $s2,40($sp)
    sw $s3,44($sp)
#endif
    sw $a2,28($sp)
    move $s0,$a2
    move $s1,$a1
    move $s2,$a0
#if INDIRECT
    li $v0,1000
    move $a0,$s2
    lw $a1,0($s1)
    lw $a2,4($s1)
    lw $a3,8($s1)
#if N32
    lw $8,12($s1)
    lw $9,16($s1)
    lw $10,20($s1)
#else
    lw $8,12($s1)
    sw $8,16($sp)
    lw $8,16($s1)
    sw $8,20($sp)
    lw $8,20($s1)
    sw $8,24($sp)
#endif
#else
    move $v0,$s2
    lw $a0,0($s1)
    lw $a1,4($s1)
    lw $a2,8($s1)
    lw $a3,12($s1)
#if N32
    lw $8,16($s1)
    lw $9,20($s1)
#else
    lw $8,16($s1)
    sw $8,16($sp)
    lw $8,20($s1)
    sw $8,20($sp)
#endif
#endif
    li $s0,0x11220001
    li $s1,0x11220002
    li $s2,0x11220003
    li $s3,0x11220004
    li $v1,0xfeedface
    syscall
    nop
    lw $t0,28($sp)
    sw $v0,0($t0)
    sw $v1,4($t0)
    sw $a3,8($t0)
#if N32
    ld $s0,32($sp)
    ld $s1,40($sp)
    ld $s2,48($sp)
    ld $s3,56($sp)
#else
    lw $s0,32($sp)
    lw $s1,36($sp)
    lw $s2,40($sp)
    lw $s3,44($sp)
#endif
    jr $ra
    addiu $sp,$sp,64
.end spawn_call
