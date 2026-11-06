# Convert the imported SGI entries to Xlib's per-session colour database.
# Xcms normalizes case and spaces; keep standard Xorg names untouched.
BEGIN { print "XCMS_COLORDB_START 0.1" }
NF >= 4 && $1 ~ /^[0-9]+$/ && $2 ~ /^[0-9]+$/ && $3 ~ /^[0-9]+$/ {
    name = ""
    for (i = 4; i <= NF; i++) name = name tolower($i)
    if (name !~ /^sgi/) next
    for (i = 1; i <= 3; i++) if ($i > 255) { bad = 1; exit 1 }
    value = sprintf("rgb:%04x/%04x/%04x", $1 * 257, $2 * 257, $3 * 257)
    if (name in colours) {
        if (colours[name] != value) { bad = 1; exit 1 }
        next
    }
    colours[name] = value
    print name "\t" value
    count++
}
END {
    if (bad || !count) exit 1
    print "XCMS_COLORDB_END"
}
