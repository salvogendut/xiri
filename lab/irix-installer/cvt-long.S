/* Exercise the conversion used by libinst on R4400/R5000. */
.set noreorder
.section .note.probe,"a",@note
.long 5, 4, 0x49524958
.asciz "Xiri"
.balign 4
.long 1

.text
.globl _start
_start:
	la	$8, cases
	li	$9, 1
again:
	lw	$12, 16($8)		/* rounding mode */
	lw	$13, 20($8)		/* expected cause and sticky flag */
	ctc1	$12, $31
	nop
	nop
	ldc1	FS, 0($8)
	nop
	cvt.d.l FD, FS
	nop
	la	$24, result
	sdc1	FD, 0($24)
	cfc1	$15, $31
	nop
	lw	$10, 8($8)
	lw	$14, 0($24)
	bne	$10, $14, finish
	nop
	lw	$11, 12($8)
	lw	$14, 4($24)
	bne	$11, $14, finish
	nop
	andi	$15, $15, 0x1004
	bne	$15, $13, finish
	nop
	addiu	$9, 1
	addiu	$8, 24
	slti	$10, $9, CASE_COUNT+1
	bnez	$10, again
	nop
	move	$9, $0
finish:
	move	$4, $9			/* first failing case, or zero */
	li	$2, 1001
	syscall
	nop
.data
.balign 8
result:	.dword 0
cases:
