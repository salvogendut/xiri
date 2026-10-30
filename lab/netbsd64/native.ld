OUTPUT_ARCH(mips)
ENTRY(_start)
PHDRS
{
    image PT_LOAD FILEHDR PHDRS FLAGS(5);
    note PT_NOTE FLAGS(4);
}
SECTIONS
{
    . = 0x00400000 + SIZEOF_HEADERS;
    .note.probe : { *(.note.probe) } :image :note
    .text : { *(.text) } :image
    .rodata : { *(.rodata) } :image
    /DISCARD/ : { *(.reginfo) *(.MIPS.abiflags) *(.pdr) *(.gnu.attributes) *(.comment) }
}
