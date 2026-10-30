# Load netbsd.gdb on GDB's command line before sourcing this file.
# These settings match IRIS's remote CPU registers, not the guest's C ABI.
set pagination off
set confirm off
set architecture mips:isa64
set mips abi n64
set mips mask-address off
set endian big
set heuristic-fence-post 0
set remotetimeout 10
