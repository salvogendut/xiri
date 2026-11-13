/* SGI _SGI_ICON records measured with the original IRIX 6.5.22m desktop.
 * Records are NUL-separated key:value fields; quoted values double quotes.
 * Backslashes are literal. Never interpret filenames as shell expressions.
 */
#ifndef XIRI_DROP_FILES_H
#define XIRI_DROP_FILES_H
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#define XIRI_DROP_LIMIT 65536
#define XIRI_DROP_FILES 256

static char *
drop_uris(const unsigned char *data, size_t length, const char *hostname,
    size_t *result_length, unsigned *file_count)
{
    if (!length || length > XIRI_DROP_LIMIT || data[length - 1] != 0)
        return NULL;
    char *out = malloc(length * 3 + XIRI_DROP_FILES * 9 + 1);
    char *value = malloc(length + 1), *name = malloc(length + 1);
    if (!out || !value || !name) { free(out); free(value); free(name); return NULL; }
    size_t pos = 0, used = 0;
    unsigned count = 0;
    while (pos < length) {
        size_t end = pos;
        while (end < length && data[end]) end++;
        if (end == pos || end == length || ++count > XIRI_DROP_FILES) goto invalid;
        unsigned fields = 0;
        while (pos < end) {
            while (pos < end && data[pos] == ' ') pos++;
            if (pos == end) break;
            size_t key = pos;
            while (pos < end && data[pos] != ':' && data[pos] != ' ') pos++;
            if (pos == end || data[pos] != ':') goto invalid;
            size_t keylen = pos++ - key, n = 0;
            if (pos < end && data[pos] == '"') {
                pos++;
                int closed = 0;
                while (pos < end) {
                    unsigned char c = data[pos++];
                    if (c == '"') {
                        if (pos < end && data[pos] == '"') pos++;
                        else { closed = 1; break; }
                    }
                    value[n++] = c;
                }
                if (!closed || (pos < end && data[pos] != ' ')) goto invalid;
            } else {
                while (pos < end && data[pos] != ' ') value[n++] = data[pos++];
            }
            value[n] = 0;
            unsigned bit = 0;
            if (keylen == 8 && !memcmp(data + key, "Category", 8)) {
                bit = 1;
                if (strcmp(value, "File")) goto invalid;
            } else if (keylen == 4 && !memcmp(data + key, "Name", 4)) {
                bit = 2;
                if (!n || value[0] != '/') goto invalid;
                memcpy(name, value, n + 1);
            } else if (keylen == 4 && !memcmp(data + key, "Host", 4)) {
                bit = 4;
                if (strcmp(value, hostname)) goto invalid;
            }
            if (fields & bit) goto invalid;
            fields |= bit;
        }
        if (fields != 7) goto invalid;
        memcpy(out + used, "file://", 7); used += 7;
        for (const unsigned char *p = (const unsigned char *)name; *p; p++) {
            unsigned c = *p;
            if ((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') ||
                (c >= '0' && c <= '9') || strchr("/-._~", c)) out[used++] = c;
            else {
                const char *hex = "0123456789ABCDEF";
                out[used++] = '%'; out[used++] = hex[c >> 4]; out[used++] = hex[c & 15];
            }
        }
        out[used++] = '\r'; out[used++] = '\n'; pos = end + 1;
    }
    out[used] = 0; free(value); free(name);
    *result_length = used; *file_count = count; return out;
invalid:
    free(out); free(value); free(name); return NULL;
}
#endif
