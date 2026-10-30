# Run from the repository root, with IRIS waiting at the PROM command prompt.
# After XIRI_GDB_READY, send the TFTP boot command through iris-ci.
source lab/indy-netbsd/debugger.gdb
target remote 127.0.0.1:1234
tbreak *main
echo XIRI_GDB_READY\n
continue
if ((unsigned long)$pc & 0xffffffff) != ((unsigned long)&main & 0xffffffff)
    echo Unexpected stop before main\n
    quit 1
end
printf "XIRI_GDB_MAIN pc=%#lx\n", $pc
info registers pc sp a0
x/4i $pc
x/s kernel_ident
tbreak *cpu_rootconf
continue
if ((unsigned long)$pc & 0xffffffff) != ((unsigned long)&cpu_rootconf & 0xffffffff)
    echo Unexpected stop before cpu_rootconf\n
    quit 1
end
printf "XIRI_GDB_ROOTCONF pc=%#lx\n", $pc
x/4i $pc
detach
# IRIS leaves the CPU stopped on detach. Resume with iris-ci start.
quit
