/* Original IRIX fixture: replace this image with an explicitly named native control. */
typedef unsigned int U;
struct reply { U value, second, error; };
extern void probe_call(U, const U *, struct reply *);
int main(int argc, char **argv)
{
    if (argc != 2) return 2;
    U av[2]={(U)argv[1],0}, ev[1]={0};
    U args[6]={(U)argv[1],(U)av,(U)ev,0,0,0};
    struct reply r;
    probe_call(1059,args,&r);
    return 3;
}
