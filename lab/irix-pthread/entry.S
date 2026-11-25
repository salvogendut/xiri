/* n32 raw child entry and fixed-address PRDA control. Write one record
 * after the worker has published its observation in ordinary shared data. */
.set noreorder
.section .note.probe,"a",@note
.long 5,4,0x49524958
.asciz "Xiri"
.balign 4
.long 1
.text
.globl _start
_start:
    li $a0,20
    li $v0,1130
    syscall
    nop
    li $t0,0x200000
    li $t1,0x1357
    sw $t1,0xc00($t0)
    la $a0,raw_entry
    li $a1,0x020000ff
    la $a2,descriptor
    move $a3,$zero
    li $8,2
    li $s0,0x5510
    li $s1,0x5511
    li $s2,0x5512
    li $s3,0x5513
    li $v0,1204
    syscall
    nop
    la $s0,record
    sw $v0,0($s0)
    sw $a3,4($s0)
    bnez $a3,report
    li $s1,100
wait_worker:
    lw $t0,8($s0)
    bnez $t0,report
    nop
    li $a0,2
    li $v0,1082
    syscall
    addiu $s1,$s1,-1
    bnez $s1,wait_worker
    nop
report:
    li $t0,0x200000
    lw $t1,0xc00($t0)
    sw $t1,84($s0)
    lw $t1,0xe00($t0)
    sw $t1,88($s0)
    lw $t1,0xe40($t0)
    sw $t1,92($s0)
    la $t1,stack_top
    sw $t1,96($s0)
    li $a0,1
    move $a1,$s0
    li $a2,100
    li $v0,1004
    syscall
    nop
    lw $t0,8($s0)
    sltiu $a0,$t0,1
    li $v0,1001
    syscall
    nop

raw_entry:
    b capture
    li $t2,1
descriptor_entry:
    li $t2,2
capture:
    la $t0,record
    sw $a0,12($t0)
    sw $a1,16($t0)
    sw $a2,20($t0)
    sw $a3,24($t0)
    sw $v0,28($t0)
    sw $v1,32($t0)
    sw $sp,36($t0)
    sw $ra,40($t0)
    sw $s0,44($t0)
    sw $s1,48($t0)
    sw $s2,52($t0)
    sw $s3,56($t0)
    li $t1,0x200000
    lw $t3,0xc00($t1)
    sw $t3,60($t0)
    lw $t3,0xe00($t1)
    sw $t3,64($t0)
    lw $t3,0xe40($t1)
    sw $t3,68($t0)
    lw $t3,0xe6c($t1)
    sw $t3,72($t0)
    lw $t3,0xe70($t1)
    sw $t3,76($t0)
    lw $t3,0xe74($t1)
    sw $t3,80($t0)
    li $t3,0x2468
    sw $t3,0xc00($t1)
    sync
    sw $t2,8($t0)
    li $a0,21
    li $a1,1
    li $v0,1130
    syscall
    nop
1:  b 1b
    nop

.data
.balign 16
descriptor:
    .word descriptor_entry,0x556677,0x020000ff,stack_top,0
record:
    .space 100
.balign 16
    .space 4096
stack_top:
