---
title: FastStone RCE
date: 2025-07-28 14:39:52 +0900
last_modified_at: 2026-06-12 14:39:52 +0900
categories: [bug hunting]
---

화이트햇 스쿨 팀 프로젝트에서 얻은 성과다.
익스플로잇에 성공하고 ZDI에 제보했지만 거절당했고, 해당 프로그램 제작자에게 연락을 넣어봤으나 아직까지도 응답이 없다...

## 1. 개요

FastStone Image Viewer에서 MRW 파일을 파싱하는 과정에서 발생하는 스택 기반 버퍼 오버 플로우로 인해 
임의 코드 실행이 가능한 취약점이다.

## 2. 분석

해당 프로그램은 fsplugin01.dll을 사용하는데, 이 dll은 raw 포맷 파일을 파싱하는데 사용된다.
이 취약점은 `sub_41CE20`함수에서 발생한다.

```c
long double __cdecl sub_41CE20(int a1, int a2, int a3, int a4)
{
  int v4; // eax
  int i; // ebx
  int v6; // eax
  unsigned __int16 *v7; // eax
  char v9[8256]; // [esp+1Ch] [ebp-206Ch] BYREF
  char *v10; // [esp+205Ch] [ebp-2Ch]
  char *v11; // [esp+2060h] [ebp-28h]
  double v12[2]; // [esp+2064h] [ebp-24h] BYREF
  int v13; // [esp+2074h] [ebp-14h]
  int v14; // [esp+2078h] [ebp-10h]
  int v15; // [esp+207Ch] [ebp-Ch]
  __int64 v16; // [esp+2080h] [ebp-8h]

  v16 = 0i64;
  qmemcpy(v12, &unk_459DEC, sizeof(v12));
  v13 = 0;
  v10 = v9;
  do
  {
    if ( v13 )
      v4 = a4;
    else
      v4 = a3;
    sub_425620(dword_4A9094, v4, 0);
    v14 = 0;
    v15 = 0;
    v11 = v10;
    while ( v14 < (int)dword_4A9534 )
    {
      for ( v15 -= a1; v15 < 0; v15 += a2 )
      {
        v16 <<= a2;
        for ( i = 0; a2 > i; i += 8 )
        {
          v6 = getc(dword_4A9094);
          LODWORD(v16) = (v6 << i) | v16;
        }
      }
      *(_WORD *)v11 = (unsigned __int64)(v16 << (64 - (unsigned __int8)a1 - v15)) >> (64 - (unsigned __int8)a1); // here
      ++v14;
      v11 += 2;
    }
    ++v13;
    v10 += 0x1020;
  }
  while ( v13 < 2 );
  v7 = (unsigned __int16 *)v9;
  v13 = 0;
  while ( (int)(dword_4A9534 - 1) > v13 )
  {
    v12[v13 & 1] = (long double)(int)abs32(*v7 - v7[2065]) + v12[v13 & 1];
    v12[(v13 & 1) == 0] = (long double)(int)abs32(v7[2064] - v7[1]) + v12[(v13 & 1) == 0];
    ++v13;
    ++v7;
  }
  return log(v12[0] / v12[1]) * 100.0;
}
```
이 함수 내부에서 전역 변수 `dword_4A9534`가 while 루프 안에서 배열에 값을 쓰는데 사용된다.
이 변수는 이미지의 너비를 저장한다.

이 값은 조작된 파일을 통해 공격자가 제어할 수 있기 때문에, 버퍼가 담을 수 있는 크기보다 더 많은 데이터를 써서 버퍼 오버플로우를 발생시킬 수 있다.

이 취약점은 AAW가 가능할 뿐만 아니라, 해당 dll에 aslr이 비활성화되어 있기 때문에 가젯을 뽑아서 ROP 체인을 구성하고 실행 흐름을 공격자가 유도할 수 있다.

## 3. PoC

실행 흐름을 조작할 수 있는 시점에서 공격자가 제어할 수 있는 데이터가 이미 스택에 존재한다.

이를 이용해 공격자는 VirtualAlloc을 호출하여 실행 권한이 있는 메모리 영역을 할당받을 수 있다.

그리고 `0x43278f: add al, 0x24 ; add esp, 0x10 ; ret`가젯을 사용하여 스택 포인터를 조정한다.

VirtualAlloc의 반환값은 rax에 저장되며, 이 값은 memcpy에 필요하다. 따라서 이후의 가젯을 사용해 셸코드를 새로 할당된 실행 가능한 메모리 영역으로 복사할 수 있다.

```text
.text:004478B4                 push    eax             ; void *
.text:004478B5                 call    _memcpy
.text:004478BA                 add     esp, 0Ch
.text:004478BD                 call    @_InitTermAndUnexPtrs$qv ; _InitTermAndUnexPtrs(void)
.text:004478C2                 pop     ebx
.text:004478C3                 pop     ecx
.text:004478C4                 pop     ecx
.text:004478C5                 pop     ebp
.text:004478C6                 retn
```
`memcpy`의 나머지 인자들은 조작된 파일을 통해 설정할 수 있다.

`0x43278f: add al, 0x24 ; add esp, 0x10 ; ret` 가젯은 `eax`레지스터의 값을 약간 변경하므로, 안전한 실행을 보장하기 위해 시작 부분에 NOP sled를 추가한다.

또한 이 NOP sled 내부에서 실행 중 `0x443456: jmp eax`가젯을 만날 수도 있다. 이 가젯에 도달하게 되면 크래시가 발생할 수 있다. 이를 방지하기 위해 상대 점프 명령어인 `EB 0A`를 넣어 문제가 되는 영역을 건너뛰도록 하고, 셸코드로 이어질 수 있도록한다.

<video controls width="100%">
  <source src="/assets/img/2026/faststone/Poc_vedio.mp4" type="video/mp4">
</video>