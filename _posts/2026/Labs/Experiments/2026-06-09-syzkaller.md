---
title: syzkaller 설치 및 사용법
date: 2025-09-29 16:44:41 +0900
categories: [Labs, Experiments]
---

구글에서 개발한 리눅스 커널의 취약점을 찾기 위한 퍼징 도구인 syzkaller의 설치 방법과 사용법을 알아보자.

wsl Ubuntu 24.04에서 진행했다.

https://github.com/google/syzkaller

## 1. 리눅스 커널 빌드

원하는 커널 소스를 가져온 뒤, 해당 디렉토리로 이동해서 다음 명령어를 입력한다.

```bash
make defconfig
make kvm_guest.config
make menuconfig
```

`make menuconfig`를 입력하면 GUI로 커널 빌드 옵션을 선택할 수 있는데, 여기서 아래의 항목들을 찾아 활성화 해준다.

```
# Coverage collection.
CONFIG_KCOV=y

# Debug info for symbolization.
CONFIG_DEBUG_INFO_DWARF4=y

# Memory bug detector
CONFIG_KASAN=y
CONFIG_KASAN_INLINE=y

# Required for Debian Stretch and later
CONFIG_CONFIGFS_FS=y
CONFIG_SECURITYFS=y
```
이 옵션들은 커널 퍼징을 위한 최소한의 옵션이다. 필요하다면 다른 옵션들을 활성화 해주자.

저장 후 컴파일을 한다.

```bash
make -j$(nproc)
```

## 2. 파일 시스템 생성

```bash
sudo apt install debootstrap
mkdir img
cd img
wget https://raw.githubusercontent.com/google/syzkaller/master/tools/create-image.sh -O create-image.sh
chmod +x create-image.sh
./create-image.sh
```

## 3. qemu 설치

```bash
sudo apt install qemu-system-x86
```

```bash
sudo qemu-system-x86_64 \
        -m 2G \
        -smp 2 \
        -kernel {사용자 경로}/linux/arch/x86/boot/bzImage \
        -append "console=ttyS0 root=/dev/sda earlyprintk=serial net.ifnames=0" \
        -drive file={사용자 경로}/img/bullseye.img,format=raw \
        -net user,host=10.0.2.10,hostfwd=tcp:127.0.0.1:10021-:22 \
        -net nic,model=e1000 \
        -enable-kvm \
        -nographic \
        -pidfile vm.pid \
        2>&1 | tee vm.log
```

성공적으로 부팅이 되었다면 다른 터미널에서 ssh를 통해 접속할 수 있다.

```bash
ssh -i {사용자 경로}/bullseye.id_rsa -p 10021 -o "StrictHostKeyChecking no" root@localhost
```

## 4. syzkaller 설치

시즈칼러 컴파일을 위한 go를 설치해야한다.

```bash
wget https://dl.google.com/go/go1.23.6.linux-amd64.tar.gz
tar -xf go1.23.6.linux-amd64.tar.gz

mv go goroot
mkdir gopath
export GOPATH=`pwd`/gopath
export GOROOT=`pwd`/goroot
export PATH=$GOPATH/bin:$PATH
export PATH=$GOROOT/bin:$PATH
```
export는 현재 터미널 세션에서만 유효하다.

```bash
git clone https://github.com/google/syzkaller
cd syzkaller
make
```

make가 완료되었으면 시즈칼러 bin 폴더에 바이너리가 생성된다. 

이제 시즈칼러를 실행하면 된다.

```bash
./bin/syz-manager -config my.cfg
```

config는 링크를 참조해서 작성하면 된다.

https://github.com/google/syzkaller/blob/master/pkg/mgrconfig/config.go

```
{
	"target": "linux/amd64",
	"http": "127.0.0.1:56741",
	"workdir": "{사용자 경로}/syzkaller/workdir",
	"kernel_obj": "{사용자 경로}/linux",
	"image": "{사용자 경로}/img/bullseye.img",
	"sshkey": "{사용자 경로}/img/bullseye.id_rsa",
	"syzkaller": "{사용자 경로}/syzkaller",
	"procs": 8,
	"type": "qemu",
	"vm": {
		"count": 1,
		"kernel": "{사용자 경로}/linux/arch/x86/boot/bzImage",
		"cmdline": "net.ifnames=0",
		"cpu": 2,
		"mem": 2048
	}
}
```
대략 이런 식으로 하면 된다.

## 5. 참고
https://www.postype.com/@cpuu/post/9075747