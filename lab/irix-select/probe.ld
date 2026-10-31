OUTPUT_ARCH(mips)
ENTRY(_start)
PHDRS
{
    text PT_LOAD FILEHDR PHDRS FLAGS(5);
    data PT_LOAD FLAGS(6);
    note PT_NOTE FLAGS(4);
}
SECTIONS
{
    . = 0x00400000 + SIZEOF_HEADERS;
    .note.probe : { *(.note.probe) } :text :note
    .text : { *(.text) } :text
    .rodata : { *(.rodata) } :text
    . = 0x00800000;
    .data : { *(.data) } :data
    .bss (NOLOAD) : { . = 0x2000 - SIZEOF(.data); } :data
    /DISCARD/ : { *(.reginfo) *(.MIPS.abiflags) *(.pdr) *(.gnu.attributes) *(.comment) }
}
