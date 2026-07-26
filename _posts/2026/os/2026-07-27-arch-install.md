---
title: 아치 리눅스 세팅
date: 2026-07-27 07:17:45 +0900
categories: [os]
---

wsl이나 vmware 말고 진짜 호스트 운영체제로 리눅스를 써보고 싶다는 생각을 하다가 이번에 아치 리눅스를 설치해보기로 했다.

>아래의 모든 과정은 윈도우가 깔린 상태이고, UEFI를 지원한다는 가정하에 작성된 글입니다.
{: .prompt-danger }

## 1. Arch Linux ISO 부팅 USB 만들기

일반 아치 리눅스 ISO 다운로드 페이지에서 토렌트를 써서 다운받거나 미러 사이트를 통해 받을 수 있는데, 나는 미러 사이트로 다운받아서 ISO의 해시 값을 검증하고 사용했다.

그리고 이 ISO와 USB를 통해 부팅 가능한 USB를 만들어야하는데, 보통 루퍼스나 UUI를 쓴다.

이거는 취향껏 선택해서 만들자.

## 2. Arch Linux installer 부팅

아치 리눅스를 설치하러면 시큐어 부트를 비활성화 해야한다.
부팅 시 f1을 눌러 BIOS/UEFI 설정에서 비활성화 할 수 있다.

그리고 부팅 메뉴에서 아까 만든 USB를 선택해서 부팅해주도록 하자.

## 3. 인터넷 연결

```bash
ping 8.8.8.8
```


만약 데스크톱이라면 유선으로 연결되어 있어서 인터넷이 잘 될텐데, 노트북이라면 연결이 되어 있지 않을 수도 있다.

```bash
iwctl
#iwctl 쉘 진입

device list
station wlan0 scan
station waln0 get-networks
station wlan0 connect "SSID_NAME"
```

## 4. 디스크 파티셔닝

나는 C드라이브에 윈도우가 설치되어 있고, E드라이브에 리눅스를 설치할 예정이다. 이 드라이브들은 논리적으로 분할한 것이 아닌 물리적으로 다른 디스크이기 때문에 바로 이렇게 진행하는 것이다.

하나의 디스크로 멀티 부팅을 하려면 과정이 조금 달라진다.

```bash
lsblk
```
명령어를 통해 어디에 리눅스를 깔아야하는지 잘 확인하도록 하자.
드라이브 이름이 나오지 않기에 용량을 보고 맞추는게 편하다.

확인했다면 

```bash
cfdisk /dev/nvmen1n1 #드라이브 이름은 다를 수 있음
```
만약 라벨 선택이 나온다면 GPT를 선택해주자.

진입했을 때 Free Space만 있는게 아닌 이미 할당된 공간들이 있다면 전부 delete해서 Free Space로 돌려주자.

New를 통해 먼저 1G를 할당한다. 이는 부트 파티션이다.

다음 New를 통해 10G를 할당한다. 이는 스왑 파티션이다.

그 다음 New를 통해 남은 공간 전부를 할당한다. 이는 루트 파티션이다.

Write를 누르고 yes를 입력한 후 quit하자.


## 5. 파티션 포맷

루트 파티션 : ext4로 포맷할 것이다.
부팅 파티션 : efi 시스템 파티션(FAT32)로 포맷할 것이다.
스왑 파티션 : 스왑 공간으로 초기화된다.

`lsblk`로 잘 확인하고 아래 명령어들을 수행하자!

```bash
mkfs.ext4 /dev/nvme1n1p3 #루트 파티션
mkfs.fat -F 32 /dev/nvme1n1p1 #부트 파티션
mkswap /dev/nvme1n1p2 #스왑 파티션
```

## 6. 파티션 마운트

먼저 루트 파티션을 마운트하자.

```bash
mount /dev/nvme1n1p3 /mnt
mkdir -p /mnt/boot/efi
mount /dev/nvme1n1p1 /mnt/boot/efi
swapon /dev/nvme1n1p2
```
위 명령어들을 실행하고 lsblk로 한 번 더 확인하자.

## 7. 기본 시스템 설치

```bash
pacstrap /mnt base linux linux-firmware sof-firmware base-devel grub efibootmgr nano networkmanager os-prober
```

## 8. fstab 생성

```bash
genfstab /mnt > /mnt/etc/fstab
```

## 9. 설치된 시스템으로 이동 및 기본 구성

```bash
arch-chroot /mnt

ln -sf /usr/share/zoneinfo/Asia/Seoul /etc/localtime
date # 확인용
hwclock --systohc
nano /etc/locale.gen #en_US를 찾아 #을 삭제 후 저장
locale-gen
nano /etc/locale.conf # LANG=en_US.UTF-8 입력 후 저장

nano /etc/hostname #원하는 호스트명 입력 후 저장
passwd # 루트 유저 비밀번호 설정
useradd -m -G wheel -s /bin/bash username #username에 원하는 이름 입력
passwd username

EDITOR=nano visudo # group whell to ... 찾아서 %whell 앞의 # 제거 후 저장
```

## 10. 시스템 업데이트

```bash
su username
sudo pacman -Syu
```

## 11. 핵심 서비스 활성화

```bash
exit #유저 쉘에서 루트 쉘로 돌아감
systemctl enable NetworkManager
grub install /dev/nvme1n1
grub-mkconfig -o /boot/grub/grub.cfg
```

## 12. 재부팅

```bash
exit # chroot 환경 종료
umount -a
reboot
```

## 13. 설치된 운영체제에 접속

재부팅 하면 grub 부트로더 화면이 뜰텐데 방향키로 조절해서 아치 리눅스를 선택해서 부팅하면 된다.

## 14. 멀티부팅 세팅

```bash
sudo nano /usr/bin/grub-mkconfig # GRUB_DISABLE_OS_PROBER 찾아서 false로 변경 후 저장
sudo grub-mkconfig -o /boot/grub/grub.cfg
```