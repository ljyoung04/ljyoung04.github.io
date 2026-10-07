---
title: Network Enumeration with Nmap
date: 2026-10-06 19:42:24 +0900
description: 네트워크 상에 존재하는 시스템들 식별하고 스캔하는데 주로 사용되는 도구인 Nmap의 사용법을 알아보자.
categories: [Labs, HTB]
---


## Host Enumeration

### 1. Host Discovery

#### 네트워크 범위 스캔

```bash
nmap 10.129.2.0/24 -sn -oA tnet 
```

`-sn` : 포트 스캔 기능 비활성화
`-oA tnet` : 결과를 tnet으로 시작하는 모든 형식으로 저장(tnet.nmap, tnet,gnmap, tnet.xml)

이 방법은 호스트의 방화벽에서 허용하는 경우에만 작동한다.

#### IP 목록 스캔

```bash
nmap -sn -oA tnet -iL hosts.lst
```

`-iL hosts.lst` 제공된 파일에 있는 대상에 대해 스캔을 수행한다. 

#### 여러 개의 IP 스캔

```bash
nmap -sn -oA tnet 10.129.2.18 10.129.2.19 10.129.2.20
nmap -sn -oA tnet 10.129.2.18-20
```

#### 단일 IP 스캔

포트 스캔을 비활성화하면 Nmap은 자동으로 ICMP echo 요청을 통해 핑 스캔을 수행한다.(-PE)
하지만 로컬 이더넷 네트워크에 있는 타겟에 대해서는 ARP를 대신 사용한다. ICMP Echo만 확인하려면
`--disable-arp-ping`으로 arp를 끄면된다.

또한 `--packet-trace`와 `--reason` 옵션으로 자세한 내용을 확인할 수 있다.


### 2. Host and Port Scanning

Nmap을 통해 스캔된 포트에 대해 얻을 수 있는 상태는 총 6가지다.
| 상태 | 의미 |
|---|---|
| `open` | 포트가 열려 있고 서비스가 연결을 수락함 |
| `closed` | 포트가 닫혀 있음. TCP의 경우 보통 `RST` 응답 |
| `filtered` | 방화벽/필터링 등으로 열림·닫힘 여부 판단 불가 |
| `unfiltered` | 접근 가능하지만 열림·닫힘 판단 불가. 주로 `ACK` Scan |
| `open\|filtered` | 응답이 없어 열려 있거나 필터링된 상태 |
| `closed\|filtered` | 닫힘 또는 필터링 상태. 주로 Idle Scan에서 발생 |

#### 열려있는 TCP 포트 찾기

기본적으로 nmap은 tcp 포트를 대상으로 스캔한다.

루트 권한으로 실행하면 SYN(-sS), 일반 사용자 권한으로 실행하면 TCP(-sT) 스캔을 수행한다.

```bash
sudo nmap 10.129.2.28 --top-ports=10
sudo nmap 10.129.2.28 -p 21 --packet-trace -Pn -n --disable-arp-ping
```

`--top-ports=10` : 가장 빈번하게 사용되는 상위 포트 10개 선택하여 스캔
`-p` : 포트 지정
`-Pn` : ICMP Echo 요청 비활성화
`-n` : DNS 역조회 비활성화

#### 열려있는 UDP 포트 찾기

UDP 스캔(-sU)은 TCP처럼 3방향 핸드세이크가 필요하지 않기 때문에 응답을 받지 못할 수도 있다.
따라서 타임아웃이 더 길어져 TCP 스캔보다 소요 시간이 더 길어진다.

#### 버전 스캔

```bash
sudo nmap 10.129.2.28 -Pn -n --disable-arp-ping --packet-trace -p 445 --reason  -sV
```

`-sV` : 서비스 스캔을 수행한다.

### 3. Saving the Results

`-oN` : .nmap 확장자
`-oG` : grepable, .gnmap 확장자
`-oX` : .xml 확장자
`-oA` : 모든 확장자로 저장

xsltproc을 사용해서 쉽게 읽을 수 있는 html 보고서를 생성할 수 있다.

```bash
xsltproc target.xml -o target.html
```

### 4. Services Enumeration

전체 포트 스캔은 시간이 오래 걸린다. 스캔 중 스페이스 바를 누르면 스캔 상태가 표시된다.

```bash
sudo nmap 10.129.2.28 -p- -sV --stats-every=5s
```

`--stats-every` : 상태를 표시할 시간 간격을 정의한다. 초(s) 또는 분(m) 단위로 설정 가능하다.

출력 상세도를 높이면 출력이 더욱 자세해진다. (`-v`, `-vv`)

다음 과정을 통해 nmap 기존에 보여주지 않던 정보를 확인할 수 있다.

```bash
sudo tcpdump -i eth0 host 10.10.14.2 and 10.129.2.28 
nc -nv 10.129.2.28 25
```

tcpdump로 패킷 캡쳐를 시작하고 해당 포트로 접속하여 네트워크 트래픽을 가로채면 더 많은 정보를 확인할 수 있다.

### 5. Nmap Scripting Engine

NSE는 nmap의 유용한 기능 중 하나이다. 이 기능을 통해 특정 서비스와 상호 작용하는 lua 스크립트를 작성할 수 있다.
이런 스크립트는 총 15개의 카테고리로 나눌 수 있다.

| 카테고리 | 설명 |
|---|---|
| `auth` | 인증 정보 및 인증 방식 확인 |
| `broadcast` | 브로드캐스트를 이용한 호스트 탐색 |
| `brute` | 계정/비밀번호 무차별 대입 |
| `default` | `-sC`로 실행되는 기본 스크립트 |
| `discovery` | 서비스 및 시스템 정보 수집 |
| `dos` | DoS 취약점 확인 |
| `exploit` | 알려진 취약점 익스플로잇 시도 |
| `external` | 외부 서비스를 이용한 정보 처리 |
| `fuzzer` | 다양한 입력을 보내 비정상 동작 탐색 |
| `info` | 대상 서비스/시스템의 추가 정보 수집 |
| `intrusive` | 대상에 영향을 줄 수 있는 공격적 스크립트 |
| `malware` | 악성코드 감염 여부 확인 |
| `safe` | 대상에 큰 영향을 주지 않는 안전한 스크립트 |
| `version` | 서비스 버전 탐지 보조 |
| `vuln` | 특정 취약점 존재 여부 확인 |

```bash
sudo nmap <target> --script <category>
sudo nmap <target> --script <script-name>,<script-name>,...
```

구체적인 스크립트 명은 `/usr/share/nmap/scripts`에서 확인할 수 있다.

```bash
nmap --script-help "smtp-*"
nmap --script-help discovery
```
이런 식으로 해당되는 NSE를 찾을 수 있다.

`-A` : 공격적인 스캔으로, OS 탐지(-O), 서비스 버전 탐지(-sV), 기본 NSE 스크립트(-sC), traceroute를 활성화하여 스캔을 수행한다.
`-O` : OS 탐지
`--traceroute` : 대상까지 가는 네트워크 경로와 hop을 추적


### 6. Performance

```bash
sudo nmap 10.129.2.0/24 -F --initial-rtt-timeout 50ms --max-rtt-timeout 100ms
sudo nmap 10.129.2.0/24 -F --max-retries 0
sudo nmap 10.129.2.0/24 -F -oN tnet.minrate300 --min-rate 300
sudo nmap 10.129.2.0/24 -F -oN tnet.T5 -T 5
```

`-F` : 상위 100개 포트를 스캔
`--initial-rtt-timeout` : 지정된 값을 초기 rtt 타임 아웃으로 설정한다.
`--max-rtt-timeout` : 지정된 값을 최대 rtt 타임 아웃으로 설정한다. 

시간을 더 짧게 설정해두면 스캔은 더 빠르게 끝나지만, 정보가 덜 발견될 수 있다.

`--max-retries` : 스캔 중에 수행할 재시도 횟수를 설정한다. 기본값은 10이다.
`--min-rate` : 초당 전송할 최소 패킷 수를 설정한다.
`-T` : 타이밍 템플릿을 설정한다. 

| 옵션 | 이름 | 특징 |
|---|---|---|
| `-T0` | Paranoid | 매우 느림, 탐지 회피 목적 |
| `-T1` | Sneaky | 느림 |
| `-T2` | Polite | 대상/네트워크 부하를 줄임 |
| `-T3` | Normal | 기본값 |
| `-T4` | Aggressive | 빠른 스캔, 안정적인 네트워크에서 자주 사용 |
| `-T5` | Insane | 매우 빠름, 패킷 손실/오탐 가능성 증가 |

## Bypass Security Measures

방화벽은 방화벽을 통과하는 네트워크 트래픽을 모니터링하고, 규칙에 따라 연결을 처리하는 방식을 결정한다.
IDS(Intrusion Detection System)는 네트워크를 스캔하여 잠재적인 공격을 탐지하고 분석하며, 탐지된 공격을 보고한다.
IPS(Intrusion Prevention System)는 잠재적인 공격이 탐지된 경우 방어 조치를 취함으로써 IDS를 보완한다.
공격에 대한 분석은 주로 패턴 매칭과 시그니처를 기반으로 한다. 

nmap의 TCP ACK 스캔(-sA)은 일반적인 SYN, TCP 스캔보다 방화벽이나 IDS/IPS에서 필터링하기 더 어려울 수 있다.
ACK 스캔은 ACK 플래그만 설정된 TCP 패킷을 보내기 때문이다.

대상 포트가 열려있든 닫혀있든, ACK 패킷이 호스트까지 도달하면 일반적으로 RST 패킷으로 응답한다.

외부에서 들어오는 SYN 패킷은 새 연결 시도로 간주되기 때문에 방화벽에서 차단당하는 경우가 많으나, ACK 패킷은 이미 존재하는 연결의 일부처럼 보일 수 있기 때문에 단순한 방화벽에서는 통과되는 경우가 있다.

```bash
sudo nmap 10.129.2.28 -p 21,22,25 -sA -Pn -n --disable-arp-ping --packet-trace
```

`-sA` ACK 스캔을 수행한다. 이 스캔으로는 포트가 open인지 closed인지 구분하지 못한다.
- -sS, -sT → 포트가 열려 있는지 확인하는 데 사용
- -sA → 주로 방화벽이 해당 포트를 필터링하고 있는지 확인하는 데 사용

```bash
sudo nmap 10.129.2.28 -p 80 -sS -Pn -n --disable-arp-ping --packet-trace -D RND:5
sudo nmap 10.129.2.28 -n -Pn -p 445 -O -S 10.129.2.200 -e tun0
```

`-D RND:5` : 스캔할 때 실제 출발지 IP와 무작위 디코이 IP 5개를 섞어 사용하여 어떤 IP에서 실제 스캔이 왔는지 구분하기 어렵게 한다.
`-S` : 다른 소스 IP 주소를 사용하여 대상을 스캔한다. 
`-e` : 지정된 인터페이스를 통해 모든 요청을 보낸다.

### 1. DNS Proxying

기본적으로 nmap은 별도로 지정하지 않는 한, 대상에 대한 추가 정보를 얻기 위해 역방향 DNS 조회를 한다.
DNS 질의는 일반적으로 허용되는 경우가 많다. 웹 서버 같은 시스템은 이름 해석이 가능해야 정상적으로 접근 가능하기 때문이다.

DNS 질의는 주로 UDP 53번 포트를 사용한다. 하지만 TCP 53을 사용하는 DNS 통신도 점차 많아지고 있다.

```bash
nmap --dns-servers <DNS1>,<DNS2> <target>
nmap --source-port 53 <target>
```

`--dns-servers` : DNS 서버를 직접 지정한다.
`--source-port` : 소스 포트를 지정한다.