/* SPDX-License-Identifier: BSD-2-Clause */
	.set noreorder
	.text
	.globl _start
_start:
	daddiu $29, $29, -32
	sd $31, 24($29)
	sd $28, 16($29)
	dla $28, _gp
	jal probe
	 nop
	ld $28, 16($29)
	ld $31, 24($29)
	jr $31
	 daddiu $29, $29, 32
