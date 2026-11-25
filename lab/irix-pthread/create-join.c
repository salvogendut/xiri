/* Build as a dynamic n32 IRIX executable with the vendor libpthread. */
#include <pthread.h>
#include <stdio.h>
#include <string.h>
#include <sys/types.h>
#include <unistd.h>

struct exchange {
    pthread_t parent;
    int distinct_thread;
    pid_t pid;
    int value;
};

static void *
run_worker(void *arg)
{
    struct exchange *data = arg;

    data->distinct_thread = !pthread_equal(data->parent, pthread_self());
    data->pid = getpid();
    data->value += 7;
    (void)write(STDOUT_FILENO, "worker ran\n", 11);
    return &data->value;
}

int
main(int argc, char **argv)
{
    struct exchange data;
    pthread_attr_t attr;
    pthread_t created;
    void *joined = NULL;
    pid_t parent_pid = getpid();
    int rc;

    if (argc > 2 || (argc == 2 && strcmp(argv[1], "system") != 0))
        return 2;
    setvbuf(stdout, NULL, _IONBF, 0);
    puts(argc == 2 ? "scope system" : "scope default");
    rc = pthread_attr_init(&attr);
    if (rc != 0) {
        printf("attr_init %d\n", rc);
        return 3;
    }
    if (argc == 2) {
        rc = pthread_attr_setscope(&attr, PTHREAD_SCOPE_SYSTEM);
        if (rc != 0) {
            printf("attr_setscope %d\n", rc);
            return 4;
        }
    }
    data.parent = pthread_self();
    data.value = 35;
    puts("before create");
    rc = pthread_create(&created, &attr, run_worker, &data);
    printf("create %d\n", rc);
    if (rc != 0)
        return 5;
    (void)pthread_attr_destroy(&attr);
    rc = pthread_join(created, &joined);
    printf("join %d\n", rc);
    if (rc != 0)
        return 6;
    printf("same_pid %d distinct_thread %d value %d returned_pointer %d\n",
        data.pid == parent_pid, data.distinct_thread, data.value, joined == &data.value);
    return !(data.pid == parent_pid && data.distinct_thread && data.value == 42 && joined == &data.value);
}
