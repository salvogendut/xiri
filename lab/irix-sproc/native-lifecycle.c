/* Extra native-policy and cleanup checks, independent of reference fixtures. */
#define main reference_main
#define child_main reference_child_main
#include "probe.c"
#undef main
#undef child_main

static U page;
int child_main(struct argument *arg) {
    U rec[64]={0x58475350,KIND,1};
    if(KIND==0) {
        reply(rec+8,C(1002,0,0,0,0,0,0));
        reply(rec+11,C(1134,0,page,3,0x182,arg->fd,0));
        reply(rec+14,C(1134,arg->local,page,3,0x112,arg->fd,0));
        reply(rec+17,C(1135,arg->local,page,0,0,0,0));
        reply(rec+20,C(1136,arg->local,page,0,0,0,0));
        reply(rec+23,C(1017,0x802000,0,0,0,0,0));
        reply(rec+26,C(1130,20,0,0,0,0,0));
        reply(rec+29,C(1131,0,arg->parent,0,0,0,0));
        reply(rec+32,C(1130,6,C(1020,0,0,0,0,0,0).value,0,0,0,0));
        reply(rec+35,C(1130,6,0x7fffffff,0,0,0,0));
        reply(rec+38,C(1130,6,arg->parent,0,0,0,0));
        reply(rec+41,C(1130,6,arg->parent,0,0,0,0));
        reply(rec+44,C(1129,child_entry,0x03000040,arg,0,0,0));
        rec[47]=*(volatile U *)arg->local;
        identity(rec+56);
        if(emit(rec))return 86;
    } else if(KIND==1) {
        *(volatile U *)arg->local=0x41;
        *(volatile U *)(arg->local+page)=0x42;
        *(volatile U *)(arg->local+2*page)=0x43;
        if(C(1130,6,arg->parent,0,0,0,0).error)return 85;
    } else {
        if(C(1130,6,arg->parent,0,0,0,0).error)return 84;
    }
    arg->word=0xabcdef01;
    return 37;
}

int main(void) {
    U rec[64]={0x58475350,KIND,0};
    struct reply r=C(1056,14,0,0,0,0,0);if(r.error)return 97;page=r.value;
    struct argument arg={C(1020,0,0,0,0,0,0).value,0,0,0,0};
    r=C(1005,"/dev/zero",2,0,0,0,0);if(r.error)return 96;arg.fd=r.value;
    r=C(1134,0,3*page,3,0x182,arg.fd,0);if(r.error)return 95;arg.local=r.value;
    *(volatile U *)arg.local=0x11;
    *(volatile U *)(arg.local+page)=0x22;
    *(volatile U *)(arg.local+2*page)=0x33;
    if(KIND==1) {
        if(C(1135,arg.local+page,page,0,0,0,0).error)return 94;
        r=C(1134,arg.local+page,page,3,0x112,arg.fd,0);
        if(r.error || r.value!=arg.local+page)return 93;
    }
    for(U i=0;i<(KIND==2?12U:1U);i++) {
        U flags=KIND==2 && (i&1)?0x03000000:0x03000040;
        arg.word=0;
        U args[6]={(U)child_entry,flags,(U)&arg,0,0,0};
        spawn_call(1129,args,&r);if(r.error){reply(rec+8,r);emit(rec);return 92;}
        if(C(1170,0,r.value,info,1,0,0).error || info[1]!=1 || info[5]!=37)return 91;
        if(arg.word!=((flags&0x40)?0xabcdef01U:0))return 90;
        rec[3]++;
    }
    rec[4]=*(volatile U *)arg.local;
    rec[5]=*(volatile U *)(arg.local+page);
    rec[6]=*(volatile U *)(arg.local+2*page);
    reply(rec+8,C(1130,14,0,0,0,0,0));
    /* The transient SHARE inheritance must not leak into ordinary fork. */
    shared_word=0x11223344;
    r=C(1002,0,0,0,0,0,0);if(r.error)return 89;
    if(r.second){shared_word=0x55667788;return 39;}
    if(C(1170,0,r.value,info,1,0,0).error || info[1]!=1 || info[5]!=39)return 88;
    rec[11]=shared_word;
    reply(rec+12,C(1135,arg.local,3*page,0,0,0,0));
    identity(rec+56);return emit(rec)?87:0;
}
