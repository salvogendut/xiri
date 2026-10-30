/* Static o32 arguments, files, and private mappings. No libc or SGI code. */
    .set noreorder
    .set noat
    .section .note.probe,"a",@note
    .long 5, 4, 0x49524958
    .asciz "Xiri"
    .balign 4
    .long 1

    .macro address reg, label
    lui \reg, %hi(\label)
    addiu \reg, \reg, %lo(\label)
    .endm
    .macro call number
    li $v0, \number
    syscall
    nop
    bne $a3, $zero, failed
    nop
    .endm
    .macro error number, expected
    li $v0, \number
    syscall
    nop
    beq $a3, $zero, failed
    nop
    li $t0, \expected
    bne $v0, $t0, failed
    nop
    .endm
    .macro value expected
    li $t0, \expected
    bne $v0, $t0, failed
    nop
    .endm
    .macro equal_string label
    address $a1, \label
    jal compare_string
    nop
    bne $v0, $zero, failed
    nop
    .endm
    .macro open_zero
    address $a0, zero_path
    li $a1, 2
    li $a2, 0
    call 1005
    move $s0, $v0
    .endm
    .macro map length, offset=0
    sw $s0, 16($sp)
    li $t0, \offset
    sw $t0, 20($sp)
    move $a0, $zero
    li $a1, \length
    li $a2, 3
    li $a3, 2
    call 1134
    move $s1, $v0
    .endm
    .macro unmap length
    move $a0, $s1
    li $a1, \length
    call 1135
    value 0
    .endm

    .text
    .globl _start
    .ent _start
_start:
    move $s7, $sp
    addiu $sp, $sp, -256

    .ifdef ARGS
    andi $t0, $s7, 7
    bne $t0, $zero, failed
    nop
    lw $v0, 0($s7)
    value 4
    lw $a0, 4($s7)
    andi $t0, $a0, 15
    bne $t0, $zero, failed
    nop
    equal_string arg0
    lw $a0, 8($s7)
    equal_string arg1
    lw $a0, 12($s7)
    equal_string empty
    lw $a0, 16($s7)
    equal_string arg3
    lw $v0, 20($s7)
    value 0
    lw $a0, 24($s7)
    equal_string env0
    lw $a0, 28($s7)
    equal_string env1
    lw $v0, 32($s7)
    value 0
    lw $v0, 36($s7)
    value 0
    lw $v0, 40($s7)
    value 0
    .endif

    .ifdef ARGS_EMPTY
    /* argc=0, argv terminator, envp terminator, static AT_NULL pair. */
    move $t1, $s7
    li $t2, 5
1:  lw $v0, 0($t1)
    value 0
    addiu $t1, $t1, 4
    addiu $t2, $t2, -1
    bne $t2, $zero, 1b
    nop
    .endif

    .ifdef FILES
    address $a0, created_path
    li $a1, 0x502 /* RDWR|CREAT|EXCL, using IRIX values */
    li $a2, 0640
    call 1005
    move $s0, $v0
    move $a0, $s0
    address $a1, file_initial
    li $a2, 5
    call 1004
    value 5
    move $a0, $s0
    call 1006
    value 0
    address $a0, created_path
    li $a1, 0x502
    li $a2, 0640
    error 1005, 17 /* EEXIST */
    address $a0, created_path
    li $a1, 9 /* WRONLY|APPEND */
    li $a2, 0
    call 1005
    move $s0, $v0
    move $a0, $s0
    address $a1, exclamation
    li $a2, 1
    call 1004
    value 1
    move $a0, $s0
    call 1006
    address $a0, created_path
    li $a1, 0
    li $a2, 0
    call 1005
    move $s0, $v0
    sw $zero, 64($sp)
    sw $zero, 68($sp)
    move $a0, $s0
    addiu $a1, $sp, 64
    li $a2, 64
    call 1003
    value 6 /* short read, not requested 64 */
    addiu $a0, $sp, 64
    equal_string file_appended
    move $a0, $s0
    addiu $a1, $sp, 64
    li $a2, 64
    call 1003
    value 0 /* EOF */
    move $a0, $s0
    call 1006
    address $a0, created_path
    li $a1, 0x201 /* WRONLY|TRUNC */
    li $a2, 0
    call 1005
    move $s0, $v0
    move $a0, $s0
    address $a1, file_final
    li $a2, 6
    call 1004
    value 6
    move $a0, $s0
    call 1006
    .endif

    .ifdef FILE_ERRORS
    move $a0, $zero
    li $a1, 0
    li $a2, 0
    error 1005, 14
    address $a0, missing_path
    error 1005, 2
    address $a0, zero_path
    li $a1, 3
    error 1005, 22
    address $a0, zero_path
    li $a1, 0x1000 /* unsupported, not silently ignored */
    error 1005, 22
    li $a0, -1
    error 1006, 9
    li $a0, -1
    addiu $a1, $sp, 64
    li $a2, 1
    error 1003, 9
    address $a0, zero_path
    li $a1, 0 /* readonly */
    li $a2, 0
    call 1005
    move $s0, $v0
    move $a0, $s0
    move $a1, $zero
    li $a2, 1
    error 1003, 14
    move $a0, $s0
    address $a1, file_initial
    li $a2, 1
    error 1004, 9
    move $a0, $s0
    call 1006
    move $a0, $s0
    error 1006, 9
    .endif

    .ifdef PARTIAL
    /* Native parent supplies a short closed pipe and an empty nonblocking one. */
    li $a0, 50
    addiu $a1, $sp, 64
    li $a2, 64
    call 1003
    value 5
    sb $zero, 69($sp)
    addiu $a0, $sp, 64
    equal_string short_data
    li $a0, 50
    addiu $a1, $sp, 64
    li $a2, 64
    call 1003
    value 0
    li $a0, 51
    error 1003, 11 /* translated EAGAIN */
    open_zero
    map 16384
    /* Pipe 53 has 8192 bytes free, no concurrent reader, and O_NONBLOCK. */
    li $a0, 53
    move $a1, $s1
    li $a2, 16384
    call 1004
    blez $v0, failed
    nop
    sltiu $t0, $v0, 16384
    beq $t0, $zero, failed
    nop
    li $a0, 53
    move $a1, $s1
    li $a2, 1
    error 1004, 11
    unmap 16384
    move $a0, $s0
    call 1006
    .endif

    .ifdef MEMORY
    open_zero
    li $s2, 8
memory_again:
    map 8192
    lw $v0, 0($s1)
    value 0
    lw $v0, 8188($s1)
    value 0
    li $t0, 0x12345678
    sw $t0, 0($s1)
    li $t0, 0x23456789
    sw $t0, 8188($s1)
    move $a0, $s1
    li $a1, 8192
    li $a2, 1
    call 1136
    value 0
    lw $v0, 0($s1)
    value 0x12345678
    lw $v0, 8188($s1)
    value 0x23456789
    move $a0, $s1
    li $a1, 8192
    li $a2, 3
    call 1136
    sw $zero, 0($s1)
    unmap 8192
    addiu $s2, $s2, -1
    bne $s2, $zero, memory_again
    nop
    move $a0, $s0
    call 1006
    .endif

    .ifdef FILE_MAP
    address $a0, map_path
    li $a1, 0
    li $a2, 0
    call 1005
    move $s0, $v0
    map 4096, 4096 /* exercise both stack arguments and nonzero file offset */
    lw $v0, 0($s1)
    value 0x22222222
    lw $v0, 4092($s1)
    value 0x22222222
    li $t0, 0x55667788
    sw $t0, 0($s1)
    lw $v0, 0($s1)
    value 0x55667788
    move $a0, $s0
    call 1006 /* mapping must survive closing fd */
    lw $v0, 0($s1)
    value 0x55667788
    unmap 4096 /* native parent verifies the original file did not change */
    .endif

    .ifdef MEM_ERRORS
    li $t0, -1
    sw $t0, 16($sp)
    sw $zero, 20($sp)
    move $a0, $zero
    li $a1, 4096
    li $a2, 3
    li $a3, 2
    error 1134, 9
    li $a3, 0x1002 /* IRIX SGI_ANYADDR must not become native MAP_ANON */
    error 1134, 22
    li $a3, 1 /* shared maps not implemented by this subset */
    error 1134, 22
    li $a3, 2
    li $t0, -4096
    sw $t0, 20($sp)
    error 1134, 22
    li $a3, 2
    li $t0, 1
    sw $t0, 20($sp)
    error 1134, 22
    sw $zero, 20($sp)
    li $a3, 2
    li $a1, 0
    error 1134, 22
    li $a1, 4096
    li $a2, 8
    li $a3, 2
    error 1134, 22
    li $a2, 3
    li $a3, 2
    li $a0, 0x10000000
    error 1134, 22
    move $a0, $zero
    li $a1, -1
    li $a3, 2
    error 1134, 12 /* native overflow/ENOMEM, before fd lookup */
    li $a0, 1
    li $a1, 4096
    error 1135, 22
    move $a0, $zero
    li $a1, 0
    error 1135, 22
    li $a1, -1
    error 1135, 22
    li $a0, 1
    li $a1, 4096
    li $a2, 3
    error 1136, 22
    move $a0, $zero
    li $a2, 8
    error 1136, 22
    li $a1, 0
    li $a2, 3
    error 1136, 22
    .endif

    .ifdef STACK_ARGS
    move $s6, $sp
    move $a0, $zero
    li $a1, 4096
    li $a2, 3
    li $a3, 2
    move $sp, $zero
    error 1134, 14
    li $a3, 2
    li $sp, 0xfffffff8 /* addition of the home slots must not wrap */
    error 1134, 14
    move $sp, $s6
    .endif

    .ifdef READONLY
    open_zero
    map 4096
    move $a0, $s1
    li $a1, 4096
    li $a2, 1
    call 1136
    sw $zero, 0($s1) /* must SIGSEGV */
    b failed
    nop
    .endif

    .ifdef UNMAPPED
    open_zero
    map 4096
    unmap 4096
    lw $t0, 0($s1) /* must SIGSEGV */
    nop
    b failed
    nop
    .endif

    li $a0, 37
    b finish
    nop
failed:
    li $a0, 99
finish:
    li $v0, 1001
    syscall
    nop
2:  b 2b
    nop
    .end _start

compare_string:
    lbu $t0, 0($a0)
    lbu $t1, 0($a1)
    bne $t0, $t1, different
    nop
    beq $t0, $zero, equal
    nop
    addiu $a0, $a0, 1
    addiu $a1, $a1, 1
    b compare_string
    nop
equal:
    jr $ra
    move $v0, $zero
different:
    jr $ra
    li $v0, 1

    .section .rodata
arg0: .asciz "fixture"
arg1: .asciz "alpha beta"
arg3: .asciz "tail"
empty: .asciz ""
env0: .asciz "XIRI_ONE=alpha beta"
env1: .asciz "XIRI_EMPTY="
zero_path: .asciz "/dev/zero"
created_path: .asciz "xiri-created"
missing_path: .asciz "xiri-no-such-file"
map_path: .asciz "map-input.bin"
file_initial: .ascii "abcde"
file_appended: .asciz "abcde!"
file_final: .ascii "saved\n"
exclamation: .ascii "!"
short_data: .asciz "short"
