---
title: 리눅스 커널 분석 세팅
date: 2026-06-05 16:50:58 +0900
last_modified_at: 2026-06-05 16:50:58 +0900
categories: [etc]
---

```bash
git clone https://compsec.snu.ac.kr/git/jaeyoung/linux-env.git
cd linux-env
./init.sh

docker compose up -d

docker compose sec -u compsec kernel-dev bash
```

접속하면 기본적으로 `/workspace` 디렉토리에 위치할 것이다.

```bash
wget -qO- https://cdn.kernel.org/pub/linux/kernel/v6.x/linux-6.12.71.tar.xz | tar xJf - -C kernels/
SRC=linux-6.12.71 OBJ=debug source scripts/envsetup.sh -s
cp $CONFIGS/kernelctf.config $KOBJ/.config
make -C $KSRC O=$KOBJ olddefconfig
make -C $KSRC O=$KOBJ -j$(nproc)
make -C $KSRC O=$KOBJ scripts_gdb
$KSRC/scripts/clang-tools/gen_compile_commands.py -d $KOBJ -o $KSRC/compile_commands.json
cp $PRJ/configs/.clangd $KSRC
```

```bash
mkfs compsec
setfs compsec

$SCRIPTS/run-vm.sh -s
```
부팅이 잘 된다면 성공이다.
