/* Run one program with an explicit, bounded environment after native ID setup. */
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

int main(int argc, char **argv)
{
    char *env[33] = {NULL};
    char line[1024];
    size_t count = 0;
    if (argc < 3) return 125;
    FILE *in = fopen(argv[1], "r");
    if (!in) { perror("session environment"); return 125; }
    while (fgets(line, sizeof(line), in)) {
        if (!strchr(line, '\n') && !feof(in)) return 125;
        line[strcspn(line, "\r\n")] = 0;
        if (!*line) continue;
        if (count == 32 || !strchr(line, '=') || line[0] == '=') return 125;
        env[count] = strdup(line);
        if (!env[count++]) return 125;
    }
    if (ferror(in) || fclose(in)) return 125;
    execve(argv[2], argv + 2, env);
    perror("session execve");
    return 126;
}
