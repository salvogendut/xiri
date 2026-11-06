# Password-free lookup data for the IRIX libc; native NSS owns authentication.
BEGIN { FS = OFS = ":" }
database == "passwd" && NF == 7 && $3 ~ /^[0-9]+$/ && $4 ~ /^[0-9]+$/ {
    if ($1 == "root" && $3 == 0) $6 = "/"
    print $1, "*", $3, $4, $5, $6, "/bin/sh"
    rows++
    next
}
database == "group" && NF == 4 && $3 ~ /^[0-9]+$/ {
    print $1, "*", $3, $4
    rows++
    next
}
{ bad = 1 }
END { if (bad || rows == 0) exit 1 }
