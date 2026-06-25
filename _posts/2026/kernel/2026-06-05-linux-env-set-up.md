---
title: 리눅스 커널 분석 세팅
date: 2026-06-05 16:50:58 +0900
last_modified_at: 2026-06-05 16:50:58 +0900
categories: [kernel]
---

## 1. 설치

```bash
git clone https://compsec.snu.ac.kr/git/jaeyoung/linux-env.git
cd linux-env
./init.sh

docker compose up -d

docker compose sec -u compsec kernel-dev bash
```

## 2. 사용법

```bash
#build guest kernel
wget -qO- https://cdn.kernel.org/pub/linux/kernel/v6.x/linux-6.12.71.tar.xz | tar xJf - -C kernels/
cp $CONFIGS/kernelctf.config $KOBJ/.config
make -C $KSRC O=$KOBJ olddefconfig
make -C $KSRC O=$KOBJ -j$(nproc)
make -C $KSRC O=$KOBJ scripts_gdb
current -s # ~/.linux.env에 현재 환경 저장

#create guest filesystem image
mkfs compsec
lsfs
setfs compsec

#launch vm
$SCRIPTS/run-vm.sh -s

#compile_commands
$KSRC/scripts/clang-tools/gen_compile_commands.py -d $KOBJ -o $KSRC/compile_commands.json

#clangd
cp $PRJ/configs/.clangd $KSRC
```
