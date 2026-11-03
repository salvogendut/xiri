/* Host regression harness; the allocator body is taken from the NetBSD fork.
 * All pages in one synthetic segment can be reclaimed. Looking outside that
 * segment is an error, even when the requested address is otherwise aligned.
 */
#include <assert.h>
#include <errno.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

typedef uint64_t paddr_t;
typedef int uvm_physseg_t;
struct vm_page { unsigned flags; paddr_t pa; struct vm_page *next; };
struct pglist { struct vm_page *head; };
#define PG_PGLCA 1
#define KASSERT assert
#define PAGE_SIZE UINT64_C(8192)
#define atop(x) ((x) / PAGE_SIZE)
#define ptoa(x) ((paddr_t)(x) * PAGE_SIZE)
#define roundup2(x, a) (((x) + (a) - 1) & ~((a) - 1))
#define rounddown2(x, a) ((x) & ~((a) - 1))
#define MIN(a, b) ((a) < (b) ? (a) : (b))
#define MAX(a, b) ((a) > (b) ? (a) : (b))
#define VM_PAGE_TO_PHYS(pg) ((pg)->pa)
#define TAILQ_INIT(q) ((q)->head = NULL)
#define TAILQ_FIRST(q) ((q)->head)
#define TAILQ_EMPTY(q) (!(q)->head)
#define TAILQ_INSERT_HEAD(q, p, field) do { (p)->next = (q)->head; (q)->head = (p); } while (0)
#define TAILQ_INSERT_TAIL(q, p, field) insert_tail(q, p)
#define TAILQ_REMOVE(q, p, field) remove_page(q, p)
#define STAT_INCR(v) ((void)0)
#define mutex_enter(p) ((void)(p))
#define mutex_exit(p) ((void)(p))
static int uvm_pglistalloc_contig_lock;
static struct vm_page pages[32];
static unsigned next_page, page_count;
static paddr_t segment_start;
static unsigned cases;

static void insert_tail(struct pglist *q, struct vm_page *p)
{
    struct vm_page **end = &q->head;
    while (*end) end = &(*end)->next;
    *end = p; p->next = NULL;
}
static void remove_page(struct pglist *q, struct vm_page *p)
{
    struct vm_page **slot = &q->head;
    while (*slot != p) { assert(*slot); slot = &(*slot)->next; }
    *slot = p->next;
}
static int uvm_reclaimable(void) { return next_page < page_count; }
static uint64_t uvm_wait_prepare(void) { return 0; }
static void uvm_wait(const char *why, uint64_t ticket)
{ (void)why; (void)ticket; abort(); }
static struct vm_page *uvm_pagealloc(void *a, int b, void *c, int d)
{ (void)a; (void)b; (void)c; (void)d; return &pages[next_page++]; }
static void uvm_pagefree(struct vm_page *p) { assert(p->flags == 0); }
static uvm_physseg_t uvm_physseg_find(paddr_t pfn, paddr_t *off)
{
    assert(pfn >= segment_start && pfn < segment_start + page_count);
    *off = pfn - segment_start; return 0;
}
static int uvm_physseg_valid_p(uvm_physseg_t s) { return s == 0; }
static paddr_t uvm_physseg_get_avail_start(uvm_physseg_t s)
{ assert(s == 0); return segment_start; }
static paddr_t uvm_physseg_get_avail_end(uvm_physseg_t s)
{ assert(s == 0); return segment_start + page_count; }
static struct vm_page *phys_to_page(paddr_t pa)
{
    if (atop(pa) < segment_start || atop(pa) >= segment_start + page_count) {
        fprintf(stderr, "INVALID page lookup %#" PRIx64 " outside [%#" PRIx64
            ", %#" PRIx64 ") in case %u\n", pa, ptoa(segment_start),
            ptoa(segment_start + page_count), cases);
        exit(1);
    }
    assert(pa % PAGE_SIZE == 0);
    return &pages[atop(pa) - segment_start];
}
#define PHYS_TO_VM_PAGE(pa) phys_to_page(pa)

/* ALLOCATOR */

static void check(paddr_t start, unsigned count, unsigned num,
    unsigned align, paddr_t low, paddr_t high, unsigned boundary)
{
    struct pglist result = { NULL };
    int possible = 0;
    unsigned allocated = 0;
    paddr_t first = 0, last = 0;
    cases++; segment_start = start; page_count = count; next_page = 0;
    for (unsigned i = 0; i < count; i++)
        pages[i] = (struct vm_page){ .pa = ptoa(start + i) };
    for (paddr_t p = start; p + num <= start + count; p++)
        if (p >= low && p + num <= high && p % align == 0 &&
            (!boundary || p / boundary == (p + num - 1) / boundary)) possible = 1;
    int error = uvm_pglistalloc_contig_aggressive(num, ptoa(low), ptoa(high),
        ptoa(align), ptoa(boundary), &result);
    assert(error == (possible ? 0 : ENOMEM));
    for (struct vm_page *p = result.head; p; p = p->next) {
        assert(p->flags == 0);
        if (allocated == 0) first = atop(p->pa);
        else assert(atop(p->pa) == last + 1);
        last = atop(p->pa); allocated++;
    }
    assert(allocated == (possible ? num : 0));
    if (possible) {
        assert(first >= low && last < high && first % align == 0);
        assert(!boundary || first / boundary == last / boundary);
    }
}

int main(void)
{
    /* Captured Indy fault: first segment page 0x4609, 16 KiB uarea. */
    check(0x4609, 8, 2, 2, 0x4002, 0xbfff, 0);
    /* Unaligned lower limits must not allocate pages below low either. */
    for (paddr_t start = 1; start <= 9; start++)
        for (unsigned count = 1; count <= 16; count++)
            for (unsigned num = 1; num <= 4; num++)
                for (unsigned align = 1; align <= 8; align *= 2)
                    for (unsigned lo = 0; lo <= 4; lo++)
                        for (unsigned hi = 0; hi < count; hi++) {
                            check(start, count, num, align, start + lo, start + count - hi, 0);
                            check(start, count, num, align, start + lo, start + count - hi, 8);
                        }
    printf("PASS %u allocator cases: holes, lower/upper limits, alignment, boundaries\n", cases);
    return 0;
}
