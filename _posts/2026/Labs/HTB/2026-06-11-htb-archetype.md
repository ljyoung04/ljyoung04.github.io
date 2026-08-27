---
title: Starting Point - Archetype
date: 2026-03-12 13:37:42 +0900
categories: [Labs, HTB]
---

## Task 1.
1433

## Task 2.
backups

## Task 3.
M3g4c0rp123

## Task 4.
mssqlclient.py

## Task 5.
xp_cmdshell

## Task 6.
winpeas

## Task 7.
ConsoleHost_history.txt

## 분석 및 플래그 획득

![1](/assets/img/2026/htb-archetype/1.png)
![2](/assets/img/2026/htb-archetype/2.png)

smb가 열려있기 때문에 접속을 시도해보자.

![3](/assets/img/2026/htb-archetype/3.png)

비밀번호와 아이디를 알아낼 수 있다.
이 정보들을 바탕으로 mssqlclient.py로 ms-sql에 접속을 시도해보자.

![4](/assets/img/2026/htb-archetype/4.png)

\ 를 / 로 바꿔줘야 접속이 된다.

help로 실행 가능한 명령어를 확인해보니 xp_cmdshell 이라는걸 확인할 수 있다. cmd 쿼리를 실행해주는 명령어인데 입력해보면 막혀있다는 것을 알 수 있다. enable_xp_cmdshell을 통해 활성화해주고 reconfigure로 적용해준다.

![5](/assets/img/2026/htb-archetype/5.png)

이제 잘 된다.

좀 더 편하게 사용하기 위해서 리버스 쉘을 열어보자. nc64.exe를 업로드해서 해보겠다.

![6](/assets/img/2026/htb-archetype/6.png)

로컬에서 nc -lvnp 4444로 포트 열고 대기 해주고, 

xp_cmdshell로 nc64.exe를 실행해서 우리 컴퓨터로 접속하게 한다.

![7](/assets/img/2026/htb-archetype/7.png)

그리고 폴더 돌아다니다 보면 유저 플래그를 획득할 수 있다.

![8](/assets/img/2026/htb-archetype/8.png)

이제 루트 플래그를 획득해야한다. 우리가 파일을 업로드할 수 있기 때문에 해당 머신의 권한 상승 가능성을 탐색하는 툴인 winpeas를 사용해볼 것이다. https://github.com/peass-ng/PEASS-ng/releases

아까와 똑같이 파일 올리고 그냥 실행하주면 알아서 탐색해준다.

결과를 보면

![9](/assets/img/2026/htb-archetype/9.png)

파워쉘 히스토리 파일이 존재한다는 것을 알 수 있다.

![10](/assets/img/2026/htb-archetype/10.png)

관리자 계정의 비밀번호를 알아냈기 때문에 관리자 계정에 접근해서 루트 플래그를 획득할 수 있을 것이다.

![11](/assets/img/2026/htb-archetype/11.png)
![12](/assets/img/2026/htb-archetype/12.png)
