---
title: 리눅스 커널 분석 세팅
date: 2026-06-05 16:50:58 +0900
last_modified_at: 2026-06-05 16:50:58 +0900
categories: [kernel]
---

## 1. 설치

```bash
git clone https://compsec.snu.ac.kr/git/jaeyoung/linux-env.git
cd linux-env
./init.sh

docker compose up -d

docker compose sec -u compsec kernel-dev bash
```

## 2. 세팅

### 1. 커널 세팅

```bash
#package update
sudo apt update && sudo apt install bear -y

#build guest kernel
wget -qO- https://cdn.kernel.org/pub/linux/kernel/v6.x/linux-6.12.71.tar.xz | tar xJf - -C kernels/
cp $CONFIGS/kernelctf.config $KOBJ/.config
make -C $KSRC O=$KOBJ olddefconfig
make -C $KSRC O=$KOBJ -j$(nproc)
make -C $KSRC O=$KOBJ scripts_gdb
current -s # ~/.linux.env에 현재 환경 저장

#create guest filesystem image
mkfs compsec
lsfs
setfs compsec

#launch vm
$SCRIPTS/run-vm.sh -s

#compile_commands
$KSRC/scripts/clang-tools/gen_compile_commands.py -d $KOBJ -o $KSRC/compile_commands.json

#clangd
cp $PRJ/configs/.clangd $KSRC
```

### 2. 헬퍼 세팅 - $SHARE/compsec/

#### Makefile
```makefile
CFLAGS := -Wall -Wextra -g -static
LDFLAGS := -lpthread

all: test help module

test: test.c
	$(CC) $(CFLAGS) -o $@ $< $(LDFLAGS)

help: help.c
	$(CC) $(CFLAGS) -o $@ $<

module:
	$(MAKE) -C helper

clean:
	rm -f test help
	$(MAKE) -C helper clean

.PHONY: all module clean
```

#### help.c
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
	
	print_and_wait("cross-cache done\n");

	return 0;
}
```
### 3. 헬퍼 세팅 - $SHARE/compsec/helper/

#### Makefile

```makefile
ifndef KOBJ
$(error KOBJ is not set. Run envsetup.sh first)
endif

KDIR ?= $(KOBJ)
BUILD := $(CURDIR)/build

all:
	mkdir -p $(BUILD)
	ln -sf $(CURDIR)/Kbuild $(BUILD)/Kbuild
	ln -sf $(CURDIR)/helper.c $(BUILD)/helper.c
	ln -sf $(CURDIR)/helper.h $(BUILD)/helper.h
	$(MAKE) -C $(KDIR) M=$(BUILD) modules

clangd:
	mkdir -p $(BUILD)
	ln -sf $(CURDIR)/Kbuild $(BUILD)/Kbuild
	ln -sf $(CURDIR)/helper.c $(BUILD)/helper.c
	ln -sf $(CURDIR)/helper.h $(BUILD)/helper.h
	$(MAKE) -C $(KDIR) M=$(BUILD) clean
	bear --output $(CURDIR)/compile_commands.json -- $(MAKE) -C $(KDIR) M=$(BUILD) modules

clean:
	rm -rf $(BUILD)
```

#### Kbuild
```text
ccflags-y += -I$(srctree)/mm -Wno-frame-larger-than
obj-m += helper.o
```

#### helper.h
```c
#ifndef _HELPER_H
#define _HELPER_H

#include <linux/ioctl.h>
#include <linux/types.h>

struct helper_arg {
	__u64 ptr;
	__u64 size;
};

#define HELPER_MAGIC		'H'
#define HELPER_ALLOC		_IOWR(HELPER_MAGIC, 0, struct helper_arg)
#define HELPER_FREE		_IOW(HELPER_MAGIC, 1, struct helper_arg)

#endif /* _HELPER_H */
```

#### helper.c
```c
#include <linux/init.h>
#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/slab.h>
#include <linux/gfp.h>
#include <linux/mm.h>
#include <linux/cpu.h>
#include "slab.h"
#include <linux/delay.h>
#include <linux/miscdevice.h>
#include <linux/fs.h>
#include <linux/uaccess.h>
#include "helper.h"

MODULE_LICENSE("GPL");

#define TARGET_CPU	1

struct slab *slab;
struct kmem_cache *cache;

static void info(void *ptr) {
	struct slab *slab;
	struct kmem_cache *cache;
	slab = virt_to_slab(ptr);
	cache = slab->slab_cache;

	pr_info("mod: [cpu %d] kmalloc(192) = 0x%px\n", smp_processor_id(), ptr);
	pr_info("mod: cache name = %s, obj size = %u, size = %u\n",
		cache->name, cache->object_size, cache->size);
}

static void test(void) {
	void *ptr;

	ptr = kmalloc(192, GFP_KERNEL);
	info(ptr);

	ptr = kmalloc(192, GFP_KERNEL);
	info(ptr);
}

static long __maybe_unused do_alloc(void *arg)
{
	test();
	// cross_cache();

	return 0;
}

/* ──────────────────────────────────────────────────
 * /dev/helper misc device
 * ────────────────────────────────────────────────── */

static int helper_open(struct inode *inode, struct file *file)
{
	return 0;
}

static int helper_release(struct inode *inode, struct file *file)
{
	return 0;
}

static long helper_ioctl(struct file *file, unsigned int cmd, unsigned long uarg)
{
	struct helper_arg arg;

	if (copy_from_user(&arg, (void __user *)uarg, sizeof(arg)))
		return -EFAULT;

	switch (cmd) {
	case HELPER_ALLOC:
		arg.ptr = (u64)kmalloc(arg.size, GFP_KERNEL);
		if (!arg.ptr)
			return -ENOMEM;
		if (copy_to_user((void __user *)uarg, &arg, sizeof(arg))) {
			kfree((void *)arg.ptr);
			return -EFAULT;
		}
		pr_info("helper: alloc(%llu) = 0x%llx\n", arg.size, arg.ptr);
		break;

	case HELPER_FREE:
		pr_info("helper: free(0x%llx)\n", arg.ptr);
		kfree((void *)arg.ptr);
		break;

	default:
		return -EINVAL;
	}

	return 0;
}

static const struct file_operations helper_fops = {
	.owner		= THIS_MODULE,
	.open		= helper_open,
	.release	= helper_release,
	.unlocked_ioctl	= helper_ioctl,
};

static struct miscdevice helper_dev = {
	.minor	= MISC_DYNAMIC_MINOR,
	.name	= "helper",
	.fops	= &helper_fops,
	.mode	= 0666,
};

static int __init mod_init(void)
{
	int ret;
	work_on_cpu(TARGET_CPU, do_alloc, NULL);	

	ret = misc_register(&helper_dev);
	if (ret) {
		pr_err("helper: misc_register failed: %d\n", ret);
		return ret;
	}
	pr_info("helper: /dev/helper registered\n");
	return 0;
}

static void __exit mod_exit(void)
{
	misc_deregister(&helper_dev);
	pr_info("helper: unloaded\n");
}

module_init(mod_init);
module_exit(mod_exit);
```

### 4. 헬퍼 빌드

```bash
# Container
make -C helper clangd
make
```

```bash
# QEMU
echo "alias m='mount -t 9p -o trans=virtio host_share /mnt'" >> ~/.bashrc
echo "alias i='insmod /mnt/compsec/helper/build/helper.ko'" >> ~/.bashrc
echo "alias r='rmmod helper'" >> ~/.bashrc
source ~/.bashrc

m
i
```
