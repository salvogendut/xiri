.set noreorder
.section .note.probe,"a",@note
.long 5, 4, 0x49524958
.asciz "Xiri"
.balign 4
.long 1
.text
.globl _start
_start:
	jal run
	nop
	move $4,$2
	li $2,1001
	syscall
.globl query
query:
	b 2f
	li $2,1056
.globl inventory
inventory:
	li $2,1040
2:
	syscall
	beqz $7,1f
	nop
	negu $2,$2
1:	jr $31
	nop
.globl emit
emit:
	move $6,$5
	move $5,$4
	li $4,1
	li $2,1004
	syscall
	jr $31
	nop
