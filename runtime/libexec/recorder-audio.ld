/* SGI rld maps one RX and one RW PT_LOAD. Both must start on page boundaries. */
OUTPUT_FORMAT("elf32-ntradbigmips")
PHDRS {
  dynamic PT_DYNAMIC FLAGS(4);
  text PT_LOAD FILEHDR PHDRS FLAGS(5);
  data PT_LOAD FLAGS(6);
}
SECTIONS {
  . = 0x41000000 + SIZEOF_HEADERS;
  .MIPS.abiflags : { *(.MIPS.abiflags) } :text
  .reginfo : { *(.reginfo) } :text
  .dynamic : { *(.dynamic) } :text :dynamic
  .hash : { *(.hash) } :text
  .dynsym : { *(.dynsym) } :text
  .dynstr : { *(.dynstr) } :text
  .rel.dyn : { *(.rel.dyn) } :text
  .text : { *(.text*) } :text
  .rodata : { *(.rodata*) } :text
  . = ALIGN(0x4000);
  _gp = ALIGN(16) + 0x7ff0;
  .got : { *(.got) } :data
  .data : { *(.data*) } :data
  .bss : { *(.bss*) } :data
  /DISCARD/ : { *(.comment) *(.eh_frame*) *(.note*) *(.pdr) }
}
