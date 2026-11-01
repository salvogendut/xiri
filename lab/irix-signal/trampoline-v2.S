/* Capture with AT, which kernels preserve across interrupts. k0/k1 are
 * kernel-reserved and are excluded. Reserve stack before saving original AT.
 * The raw sigreturn restores the interrupted context, not this call frame. */
.set noreorder
.set noat
.text
/* o32 GAS treats sd as a register-pair macro under gp32. Encode the actual
 * MIPS III SD instruction explicitly so both ABIs capture one 64-bit GPR. */
.macro save_gpr reg,off
    .word 0xfc200000 | (\reg << 16) | \off
.endm
.globl signal_trampoline
.ent signal_trampoline
signal_trampoline:
    addiu $sp,$sp,-32
    .word 0xffa10000 /* sd AT,0(SP), a real MIPS III instruction */
    lui $1,%hi(signal_entry)
    addiu $1,$1,%lo(signal_entry)
    save_gpr 0,0
    save_gpr 0,8
    save_gpr 2,16
    save_gpr 3,24
    save_gpr 4,32
    save_gpr 5,40
    save_gpr 6,48
    save_gpr 7,56
    save_gpr 8,64
    save_gpr 9,72
    save_gpr 10,80
    save_gpr 11,88
    save_gpr 12,96
    save_gpr 13,104
    save_gpr 14,112
    save_gpr 15,120
    save_gpr 16,128
    save_gpr 17,136
    save_gpr 18,144
    save_gpr 19,152
    save_gpr 20,160
    save_gpr 21,168
    save_gpr 22,176
    save_gpr 23,184
    save_gpr 24,192
    save_gpr 25,200
    save_gpr 0,208
    save_gpr 0,216
    save_gpr 28,224
    save_gpr 29,232
    save_gpr 30,240
    save_gpr 31,248
    .word 0xdfa20000 /* ld V0,0(SP): original AT */
    save_gpr 2,8
    addiu $v0,$sp,32
    save_gpr 2,232 /* original entry SP */
    addiu $sp,$sp,-64
    jal signal_body
    nop
    lui $1,%hi(signal_entry)
    addiu $1,$1,%lo(signal_entry)
    lw $a2,36($1)
    bltz $a2,1f
    lw $a0,52($1)
    b 2f
    move $a1,$0
1:  move $a1,$a0
    move $a0,$0
2:
#if INDIRECT
    move $a3,$a2
    move $a2,$a1
    move $a1,$a0
    li $a0,1088
    li $v0,1000
#else
    li $v0,1088
#endif
    syscall
    nop
    /* Unexpected return is captured as a failed fixture, never hidden. */
    li $a0,89
    li $v0,1001
    syscall
    nop
3:  b 3b
    nop
.end signal_trampoline
