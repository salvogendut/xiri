# Retain startup, every descendant event and every signal. The parent spins
# after its child fails exec; keep that unbounded repetition on the guest disk.
/^[ \t]*[0-9]+[ \t]+[0-9]+[ \t]+[^ \t]+[ \t]+[A-Z]+/ {
    if ($3 == "xwsh" && $4 == "MISC" && !parent) parent = $1
    if ($1 == parent) count++
    keep = ($1 != parent || count <= 2000 || $4 == "PSIG")
}
keep { print }
