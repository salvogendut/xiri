/* Explicit FPU state controls, even though the C observer uses soft-float. */
.set noreorder
.set hardfloat
.text
.globl signal_fpu_set
signal_fpu_set:
    ldc1 $f0,0($a0)
    ldc1 $f2,8($a0)
    ldc1 $f20,16($a0)
    ldc1 $f22,24($a0)
    ctc1 $a1,$31
    jr $ra
    nop
.globl signal_fpu_get
signal_fpu_get:
    sdc1 $f0,0($a0)
    sdc1 $f2,8($a0)
    sdc1 $f20,16($a0)
    sdc1 $f22,24($a0)
    cfc1 $8,$31
    sw $8,32($a0)
    jr $ra
    nop
