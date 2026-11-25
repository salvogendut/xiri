/* Freestanding n32 probes for worker, signal, lock and stack-guard behavior. */
typedef unsigned int word;
#define PTR(x) ((word)(x))
#define THREAD_FLAGS 0x020000ff
#define PR_EVENT 0x04000000
#define USYNC_INTR_BLOCK 2
#define USYNC_UNBLOCK 4

__asm__(".pushsection .note.probe,\"a\",@note\n"
    ".long 5,4,0x49524958\n.asciz \"Xiri\"\n.balign 4\n.long 1\n.popsection");

static int
irix_call(word n, word x, word y, word z, word w, word fd)
{
	register word v0 __asm__("$2") = n;
	register word a0 __asm__("$4") = x, a1 __asm__("$5") = y;
	register word a2 __asm__("$6") = z, a3 __asm__("$7") = w;
	register word a4 __asm__("$8") = fd, a5 __asm__("$9") = 0;
	__asm__ volatile("syscall\n\tnop" : "+r"(v0), "+r"(a0), "+r"(a1),
	    "+r"(a2), "+r"(a3), "+r"(a4), "+r"(a5) : : "memory", "$1", "$3", "$10",
	    "$11", "$12", "$13", "$14", "$15", "$24", "$25", "hi", "lo");
	return a3 ? -(int)v0 : (int)v0;
}

#define call(n, a, b, c, d) irix_call(n, a, b, c, d, 0)

static void
number(const char *label, int value)
{
	unsigned n = value < 0 ? -(unsigned)value : (unsigned)value;
	char line[60], digits[10];
	unsigned i = 0, j = 0;
	while (*label)
		line[i++] = *label++;
	line[i++] = '=';
	if (value < 0)
		line[i++] = '-';
	do {
		digits[j++] = '0' + n % 10;
		n /= 10;
	} while (n);
	while (j)
		line[i++] = digits[--j];
	line[i++] = '\n';
	call(1004, 1, PTR(line), i, 0);
}

static char stack[4][1280] __attribute__((aligned(16)));
static word ready[4], release[4];
#if defined(WAIT_WAKE) || defined(WAIT_PAIR)
static word key[2];
static int results[4];

/* n32 libpthread supplies version 1002, a 64-bit address and two shorts.
 * Unused fields are zero in this control. */
struct request {
	word version, pad;
	unsigned long long address;
	unsigned short policy, flags;
	word reserved[12];
};

/* Each worker supplies its own argument record for the same lock word. */
static struct request wait_req[2], wake_req[2];

static int
sync_call(unsigned op, unsigned index)
{
	struct request *req = op == USYNC_INTR_BLOCK ? &wait_req[index] : &wake_req[index];
	return call(1223, op, PTR(req), 0, 0);
}
#endif

static int
wait_flag(word *flag, word value)
{
	for (int i = 0; i < 150; i++) {
		if (__atomic_load_n(flag, __ATOMIC_ACQUIRE) >= value)
			return 1;
		call(1082, 1, 0, 0, 0);
	}
	return 0;
}

#ifdef EVENT_SIGNAL
#ifdef EVENT_PRIVATE
#define EVENT_SIGNO 47
#else
#define EVENT_SIGNO 16
#endif
static word event_mask[4] = {
	[(EVENT_SIGNO - 1) / 32] = 1U << ((EVENT_SIGNO - 1) % 32)
};
static word sent_to_worker;
static word event_info[32];
static int event_result, event_again;
#endif

static void
worker(word i)
{
#ifdef EVENT_SIGNAL
	if (i == 1) {
		word limit[2] = {0, 500000000}, zero[2] = {0, 0};
		number("worker_block", call(1164, 1, PTR(event_mask), 0, 0));
		__atomic_store_n(&ready[i], 1, __ATOMIC_RELEASE);
		wait_flag(&sent_to_worker, 1);
		event_result = call(1166, PTR(event_mask), PTR(event_info), PTR(limit), 0);
		event_again = call(1166, PTR(event_mask), 0, PTR(zero), 0);
		__atomic_store_n(&ready[i], 2, __ATOMIC_RELEASE);
	} else
#endif
		__atomic_store_n(&ready[i], 1, __ATOMIC_RELEASE);
#ifdef WAIT_WAKE
	if (i == 0) {
		for (unsigned step = 0; step < 4; step++) {
			results[step] = sync_call(USYNC_INTR_BLOCK, step == 0 ? 0 : 1);
			__atomic_store_n(&ready[i], step + 2, __ATOMIC_RELEASE);
		}
	}
#elif defined(WAIT_PAIR)
	results[i] = sync_call(USYNC_INTR_BLOCK, i);
	__atomic_store_n(&ready[i], 2, __ATOMIC_RELEASE);
#endif
	while (!__atomic_load_n(&release[i], __ATOMIC_ACQUIRE))
		call(1082, 1, 0, 0, 0);
	call(1130, 21, 1, 0, 0);
	for (;;) {}
}

static int
spawn(unsigned i, word flags)
{
	word desc[] = {PTR(worker), i, flags, PTR(stack[i] + sizeof(stack[i])), 0};
	return call(1204, PTR(worker), flags, PTR(desc), 0);
}

void
_start(void)
{
	int status = 1;
#ifdef SIGNAL_POLL
	/* Exercise the event worker's wait independently of worker creation. */
	const word sigusr1 = 16;
	word set[4] = {1U << (sigusr1 - 1), 0, 0, 0};
	static word info[32];
	word interval[2] = {0, 10000000}, zero[2] = {0, 0};
	int blocked = call(1164, 1, PTR(set), 0, 0);
	number("block", blocked);
	if (blocked != 0)
		goto done;
	int empty = call(1166, PTR(set), PTR(info), PTR(interval), 0);
	number("empty_wait", empty);
	int pid = call(1020, 0, 0, 0, 0);
	if (pid <= 0 || call(1037, pid, sigusr1, 0, 0) != 0)
		goto done;
	int pending = call(1166, PTR(set), PTR(info), PTR(zero), 0);
	word signo = info[0];
	number("pending_wait", pending);
	number("signal_number", signo);
	int consumed = call(1166, PTR(set), PTR(info), PTR(zero), 0);
	number("after_consume", consumed);
	/* A returned EAGAIN alone cannot distinguish sleeping from a spin. */
	int before[2], after[2];
	interval[1] = 200000000;
	if (call(1128, PTR(before), 0, 0, 0) != 0)
		goto done;
	int timed = call(1166, PTR(set), 0, PTR(interval), 0);
	if (call(1128, PTR(after), 0, 0, 0) != 0)
		goto done;
	int ms = (after[0] - before[0]) * 1000 + (after[1] - before[1]) / 1000;
	number("timed_wait", timed);
	number("elapsed_ms", ms);
	interval[1] = 1000000000;
	int invalid = call(1166, PTR(set), 0, PTR(interval), 0);
	number("invalid_timeout", invalid);
	status = empty != -11 || pending != (int)sigusr1 || signo != sigusr1 ||
	    consumed != -11 || timed != -11 || ms < 180 || invalid != -22;
	goto done;
#endif
#if defined(WAIT_WAKE) || defined(WAIT_PAIR)
	for (unsigned i = 0; i < 2; i++) {
		wait_req[i].version = wake_req[i].version = 1002;
		wait_req[i].policy = wake_req[i].policy = 1;
		wait_req[i].address = wake_req[i].address = PTR(&key[i]);
	}
#endif
#ifdef WAIT_PAIR
	/* The two workers pass different records for the same lock. */
	wait_req[1].address = wait_req[0].address;
	/* libpthread initializes the policy only on its blocking path. */
	wake_req[0].policy = 0xffff;
#endif
	int init = call(1130, 20, 0, 0, 0);
	number("init", init);
	if (init != 0)
		goto done;
#ifdef STACK_GUARD_BOUNDS
	/* Reserve adjacent private and shared pages before starting a worker. */
	const word base = 0x30000000, page = 8192;
	int zero = call(1005, PTR("/dev/zero"), 2, 0, 0);
	if (zero < 0 ||
	    irix_call(1134, base, page * 2, 3, 0x12, zero) != (int)base ||
	    irix_call(1134, base + page * 2, page, 3, 0x11, zero) !=
	    (int)(base + page * 2))
		goto done;
#endif
#ifdef WAIT_PAIR
	/* A wake can precede the first nsproc as well as the first wait. */
	int prepost = sync_call(USYNC_UNBLOCK, 0);
	number("prepost", prepost);
	if (prepost != 0 || sync_call(USYNC_INTR_BLOCK, 0) != 0)
		goto done;
	wake_req[0].policy = 0;
#endif
	int first = spawn(0, THREAD_FLAGS);
	number("ordinary", first);
	if (first < 0 || !wait_flag(&ready[0], 1))
		goto done;
#ifdef EVENT_SIGNAL
	int event = spawn(1, THREAD_FLAGS | PR_EVENT);
	number("event", event);
	if (event < 0 || !wait_flag(&ready[1], 1))
		goto done;
	int sent = call(1130, 21, 4, event, EVENT_SIGNO);
	__atomic_store_n(&sent_to_worker, 1, __ATOMIC_RELEASE);
	number("send", sent);
	if (!wait_flag(&ready[1], 2))
		goto done;
	number("received", event_result);
	number("signo", event_info[0]);
	number("code", event_info[1]);
	number("again", event_again);
	__atomic_store_n(&release[1], 1, __ATOMIC_RELEASE);
#ifdef EVENT_PRIVATE
	/* Both donors accept the request but omit 47 from this wait. */
	status = sent != 0 || event_result != -11 || event_info[0] != 0 ||
	    event_again != -11;
#else
	status = sent != 0 || event_result != EVENT_SIGNO ||
	    event_info[0] != EVENT_SIGNO || event_again != -11;
#endif
#elif defined(WAIT_WAKE)
	int early1 = sync_call(USYNC_UNBLOCK, 1);
	int early2 = sync_call(USYNC_UNBLOCK, 1);
	number("early_other_wake1", early1);
	number("early_other_wake2", early2);
	call(1082, 4, 0, 0, 0);
	word before = __atomic_load_n(&ready[0], __ATOMIC_ACQUIRE);
	number("before_wake", before);
	int wake = sync_call(USYNC_UNBLOCK, 0);
	number("wake", wake);
	if (!wait_flag(&ready[0], 2))
		goto done;
	call(1082, 4, 0, 0, 0);
	word observed = __atomic_load_n(&ready[0], __ATOMIC_ACQUIRE);
	number("after_two_early_wakes", observed);
	/* A third wait on key 1 must need a fresh wake. */
	int last = sync_call(USYNC_UNBLOCK, 1);
	number("final_wake", last);
	if (!wait_flag(&ready[0], 5))
		goto done;
	number("blocked_return", results[0]);
	number("credit1_return", results[1]);
	number("credit2_return", results[2]);
	number("final_wait_return", results[3]);
	status = early1 || early2 || wake || last || before != 1 ||
	    observed != 4 || results[0] || results[1] || results[2] || results[3];
#elif defined(WAIT_PAIR)
	int second = spawn(1, THREAD_FLAGS);
	number("second", second);
	if (second < 0 || !wait_flag(&ready[1], 1))
		goto done;
	call(1082, 4, 0, 0, 0);
	if (sync_call(USYNC_UNBLOCK, 0) != 0)
		goto done;
	/* Either worker may win. Exactly one may return per wake. */
	for (int i = 0; i < 150; i++) {
		if (__atomic_load_n(&ready[0], __ATOMIC_ACQUIRE) == 2 ||
		    __atomic_load_n(&ready[1], __ATOMIC_ACQUIRE) == 2)
			break;
		call(1082, 1, 0, 0, 0);
	}
	call(1082, 4, 0, 0, 0);
	word count = (__atomic_load_n(&ready[0], __ATOMIC_ACQUIRE) == 2) +
	    (__atomic_load_n(&ready[1], __ATOMIC_ACQUIRE) == 2);
	number("returned_after_one_wake", count);
	if (count != 1 || sync_call(USYNC_UNBLOCK, 0) != 0 ||
	    !wait_flag(&ready[0], 2) || !wait_flag(&ready[1], 2))
		goto done;
	number("first_return", results[0]);
	number("second_return", results[1]);
	__atomic_store_n(&release[1], 1, __ATOMIC_RELEASE);
	status = results[0] != 0 || results[1] != 0;
#elif defined(STACK_GUARD_BOUNDS)
	/* A copy into the guard must fail while its neighbour stays writable.
	 * Reading from /dev/zero tests this without terminating the worker. */
	int protect = call(1136, base, 1, 0, 0);
	int blocked = call(1003, zero, base, 1, 0);
	int neighbour = call(1003, zero, base + page, 1, 0);
	int restore = call(1136, base, page, 3, 0);
	int writable = call(1003, zero, base, 1, 0);
	number("protect", protect);
	number("guard_copy", blocked);
	number("neighbour_copy", neighbour);
	number("restore", restore);
	number("restored_copy", writable);
	/* Crossing into a shared page must leave both pages writable. */
	int mixed = call(1136, base + page, page * 2, 0, 0);
	int private_copy = call(1003, zero, base + page, 1, 0);
	int shared_copy = call(1003, zero, base + 2 * page, 1, 0);
	int prda = call(1136, 0x00200000, page, 0, 0);
	number("mixed_range", mixed);
	number("private_copy", private_copy);
	number("shared_copy", shared_copy);
	number("prda", prda);
	status = protect || blocked != -14 || neighbour != 1 || restore ||
	    writable != 1 || mixed != -122 || private_copy != 1 ||
	    shared_copy != 1 || prda != -122;
#elif defined(STACK_GUARD)
	int fd = call(1005, PTR("/dev/zero"), 2, 0, 0);
	int addr = irix_call(1134, 0, 8192, 3, 2, fd);
	if (fd < 0 || addr <= 0)
		goto done;
	volatile word *marker = (void *)(word)addr;
	*marker = 37;
	int protect = call(1136, addr, 8192, 0, 0);
	number("guard_none", protect);
	int restore = call(1136, addr, 8192, 3, 0);
	number("guard_rw", restore);
	if (restore)
		goto done;
	number("marker", *marker);
	status = protect != 0 || *marker != 37;
#else
	int event = spawn(1, THREAD_FLAGS | PR_EVENT);
	number("event", event);
	if (event < 0 || event == first || !wait_flag(&ready[1], 1))
		goto done;
	number("event_started", 1);
	int duplicate = spawn(2, THREAD_FLAGS | PR_EVENT);
	number("second_event", duplicate);
	if (duplicate < 0 || duplicate == event || duplicate == first)
		goto done;
	int started = wait_flag(&ready[2], 1);
	number("second_started", started);
	if (!started)
		goto done;
	__atomic_store_n(&release[2], 1, __ATOMIC_RELEASE);
	__atomic_store_n(&release[1], 1, __ATOMIC_RELEASE);
	call(1082, 10, 0, 0, 0);
	/* Keep the ordinary peer alive across event-thread exit. */
	int replacement = spawn(3, THREAD_FLAGS | PR_EVENT);
	number("replacement", replacement);
	if (replacement < 0 || replacement == first)
		goto done;
	started = wait_flag(&ready[3], 1);
	number("replacement_started", started);
	if (!started)
		goto done;
	__atomic_store_n(&release[3], 1, __ATOMIC_RELEASE);
	status = 0;
#endif
done:
	__atomic_store_n(&release[0], 1, __ATOMIC_RELEASE);
	call(1001, status, 0, 0, 0);
	for (;;) {}
}
