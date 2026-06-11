---
title: Starting Point - Sequel
date: 2026-03-09 15:16:34 +0900
categories: [htb]
---

## Task 1.
3306

## Task 2.
MairaDB

## Task 3.
-u 

## Task 4.
root

## Task 5.
\*

## Task 6.
;

## Task 7.
htb

## 분석 및 플래그 획득

![1](/assets/img/2026/htb-sequel/1.png)
mariaDB가 3306 포트로 열려있는 것을 확인

maridadb -u root -h 10.129.8.234 --ssl=0 로 접속

![2](/assets/img/2026/htb-sequel/2.png)
![3](/assets/img/2026/htb-sequel/3.png)