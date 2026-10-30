OUTPUT_ARCH(mips)
ENTRY(_start)
PHDRS
{
    image PT_LOAD FILEHDR PHDRS FLAGS(5);
    data PT_LOAD FLAGS(6);
    note PT_NOTE FLAGS(4);
}
SECTIONS
{
    . = 0x00400000 + SIZEOF_HEADERS;
    .note.probe : { *(.note.probe) } :image :note
    .text : { *(.text) } :image
    .rodata : { *(.rodata) } :image
    . = 0x00600000;
    .data : { *(.data) } :data
    .bss (NOLOAD) : { *(.bss) } :data
    .poison 0 : { *(.poison) } :NONE
    /DISCARD/ : { *(.reginfo) *(.MIPS.abiflags) *(.pdr) *(.gnu.attributes) *(.comment) }
}
