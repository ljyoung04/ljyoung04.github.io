---
title: Codex Security
date: 2026-06-22 20:55:42 +0900
categories: [CS, AI]
---

codex security는 codex용 보안 검토 플러그인이다. 코드의 취약점을 검사하고, 취약점의 타당성을 검증하여 보안 문제를 찾아낼 수 있다.

## 1. Node.js 설치

```bash
# nvm 다운로드 및 설치:
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash

# Node.js 다운로드 및 설치:
nvm install 24

# Node.js 버전 확인:
node -v # "v24.17.0"가 출력되어야 합니다.
nvm current # "v24.17.0"가 출력되어야 합니다.

# Verify the Node.js version:
node -v # Should print "v24.17.0".

# npm 버전을 확인:
npm -v # 11.13.0가 출력되어야 합니다.
```

## 2. codex security 설치

```bash
codex plugin add codex-security@openai-curated
```

## 3. 일반 보안 스캔

처음 검토하거나 일상적인 저장소/컴포넌트 점검에는 일반 보안 스캔을 사용한다. 저장소 전체를 볼 수도 있고, monorepo처럼 범위가 큰 경우 특정 폴더만 지정할 수도 있다.

```text
Use $codex-security:security-scan to scan this repository for security vulnerabilities.
```

특정 컴포넌트만 보고 싶다면 범위를 명확히 적는다.

```text
Use $codex-security:security-scan to scan this repository for security vulnerabilities, focusing on the services/billing component.
```

스캔을 시작할 때 확인할 것은 다음과 같다.

- Scan type은 `Codebase`로 둔다.
- Deep scan은 끈 상태로 시작한다.
- Codebase, Current branch, Last commit이 의도한 대상인지 확인한다.
- Scan area를 `Entire codebase` 또는 repository-relative folder로 지정한다.
- threat-model guidance는 실제로 리뷰 방향을 바꿀 정보가 있을 때만 넣는다.

threat-model guidance에는 공격자가 제어할 수 있는 입력, trust boundary, 민감한 동작, 우선적으로 볼 영역처럼 코드만으로 파악하기 어려운 정보를 넣는 것이 좋다. `AGENTS.md`에 제품 surface, trust boundary, 검증 명령, 제외할 영역을 적어두면 스캔 품질을 높이는 데 도움이 된다.

스캔은 대략 다음 순서로 진행된다.

1. Threat modeling: 자산, entry point, trust boundary, security invariant를 식별한다.
2. Finding discovery: 취약점 후보와 source-to-sink path를 찾는다.
3. Validation: 후보를 테스트하거나 근거를 검증한다.
4. Attack-path analysis: 실제 도달 가능성, 영향도, 심각도를 평가한다.
5. Finalization: 구조화된 결과를 검증하고 `report.md`를 생성한다.

결과를 볼 때는 target, revision, scan area가 맞는지 먼저 확인한다. 그 다음 coverage, deferred area, follow-up area를 읽고, 각 finding의 attacker-controlled input, sink, 검증 방법, 불확실성, reachability, severity rationale, remediation을 확인한다. 근거가 약한 finding은 그대로 받아들이지 말고, 사람이 accepted 상태로 판단한 finding만 수정 단계로 넘기는 것이 안전하다.

스캔 결과는 workspace에서 보는 것이 기본이고, 공유나 보관이 필요하면 `report.md`를 사용한다. 내부적으로는 `scan-manifest.json`, `findings.json`, `coverage.json`도 보존된다.

## 4. Deep scan

Deep scan은 일반 스캔보다 느리지만 더 포괄적으로 찾고 결과의 변동성을 줄이기 위한 모드다. 첫 실행부터 deep scan을 돌리기보다는 일반 스캔 결과를 먼저 검토한 뒤, 더 깊은 검토가 필요할 때 사용하는 흐름이 권장된다.

```text
Use $codex-security:deep-security-scan to run a deep security scan of this repository.
```

monorepo의 특정 서비스만 깊게 보고 싶다면 경로를 직접 지정한다.

```text
Use $codex-security:deep-security-scan to run a deep security scan of /absolute/path/to/repository/services/payments.
```

일반 스캔과 deep scan의 차이는 다음과 같다.

| 항목 | 일반 스캔 | Deep scan |
| --- | --- | --- |
| 용도 | 첫 검토, 일상적인 저장소/폴더 점검 | 일반 스캔 이후 더 철저한 검토 |
| 변동성 | 일반적 | 더 낮음 |
| 범위 | 저장소 또는 명시한 폴더 | 저장소 또는 명시한 폴더 |
| 실행 시간/리소스 | 상대적으로 낮음 | 상대적으로 높음 |
| PR/diff 검토 | 별도 change-review workflow 사용 | 지원하지 않음 |

Deep scan을 시작할 때는 Scan type이 `Codebase`이고 Deep scan이 켜져 있는지 확인한다. capability preflight에서 설정 변경을 제안하면 변경 내용을 정확히 보고, 내 환경에 맞을 때만 적용한다. 재시작이 필요하다는 안내가 나오면 새 thread에서 다시 시작한다.

Deep scan도 일반 스캔과 같은 findings workspace와 `report.md`를 만든다. 다만 더 넓게 탐색했더라도 coverage summary, deferred surface, proof gap이 남아 있다면 그 한계를 함께 보고 판단해야 한다.

## 5. 코드 변경사항 보안 리뷰

PR, commit, branch range, local patch처럼 특정 Git change set에서 새로 들어온 보안 regression을 확인할 때는 `security-diff-scan`을 사용한다. 이 workflow는 저장소 전체 audit이 아니라 변경된 source-like file과 직접 관련된 supporting code를 검토하는 방식이다.

아직 commit하지 않은 변경사항을 보려면 다음처럼 요청한다.

```text
Use $codex-security:security-diff-scan to review my current uncommitted changes for security regressions.
```

branch range나 commit 범위를 지정할 때는 base와 head를 명확히 쓴다.

```text
Use $codex-security:security-diff-scan to review the changes from origin/main to HEAD for security regressions. Focus on authentication, authorization, input handling, filesystem access, network requests, and secrets.
```

시작 전에 확인할 것은 다음과 같다.

- Scan type이 `Changes`인지 확인한다.
- Codebase, Current branch, Last commit이 맞는지 확인한다.
- Changes to review에서 `Uncommitted changes`, latest commit, base/head revision 중 의도한 범위를 고른다.
- 요약이 내가 리뷰하려던 변경사항과 일치하는지 확인한다.

이 workflow는 다른 branch로 checkout하지 않는다. 필요한 revision이 로컬에 없다면 먼저 fetch하거나, 로컬에 있는 base/head를 제공해야 한다.

CI/CD에서도 사용할 수 있다. 핵심은 base/head revision을 정확히 resolve하고, read-only sandbox에서 Codex CLI를 실행하고, Markdown 결과를 artifact나 PR comment로 남기는 것이다. 처음부터 required check로 막기보다는 advisory comment로 시작해서 prompt와 결과 품질을 조정하는 편이 좋다.

## 6. 기존 보안 backlog triage

이미 존재하는 scanner 결과, CVE/GHSA, advisory, bug bounty report, Jira/Linear ticket, GitHub security finding 등을 저장소 기준으로 검토하고 우선순위를 정할 때는 `triage-finding`을 사용한다.

```text
Use $codex-security:triage-finding to triage these existing security findings against this repository:

[Paste the findings or provide the artifact path.]
```

Jira나 Linear에서 가져올 때는 source issue를 바꾸지 말라고 명시하는 것이 좋다.

```text
Use $codex-security:triage-finding to import and triage the security findings from [Jira or Linear issue URLs, identifiers, or query] against this repository.
Do not change the source issues.
```

GitHub findings를 가져올 때는 code scanning, Dependabot vulnerabilities and malware, security advisories, private vulnerability reports, all 중 어떤 source를 볼지 지정한다. GitHub Issues는 기본 source에 포함되지 않으므로 이슈까지 보고 싶다면 별도로 명시해야 한다.

Triage는 read-only static analysis다. Codex는 각 finding을 아직 증명되지 않은 주장으로 보고, repository evidence만으로 다음을 확인한다.

- claimed attacker-controlled source
- 관련 security control
- vulnerable sink
- reachable path
- product surface와 trust boundary
- supporting evidence, counterevidence, proof gap

결과 verdict는 다음 세 가지다.

| Verdict | 의미 |
| --- | --- |
| `confirmed` | 저장소 근거상 취약한 경로가 전제 조건에서 도달 가능하고 지원되는 보안 경계를 넘는다. |
| `not_actionable` | 영향 없는 버전, 도달 불가능한 경로, 유효한 guard, 배포되지 않는 surface 등으로 claim이 반박된다. |
| `needs_review` | 정적 근거만으로 판단하기 어렵고 런타임, 환경, 정책, 누락 정보가 필요하다. |

`confirmed`와 `needs_review`는 각각 별도 queue에서 `P0`, `P1`, `P2`처럼 exploitability 기준으로 rank가 붙는다. 이 rank는 scanner severity score가 아니라 해당 결과 묶음 안에서의 처리 우선순위다.

Triage가 끝나면 source identifier가 유지되는지, 각 finding마다 verdict와 confidence가 있는지, 불확실성이 명확히 기록됐는지 본다. `confirmed`는 사람이 받아들인 뒤 `fix-finding`으로 넘기고, `needs_review` 중 런타임 검증이 필요한 것은 `$codex-security:validation`으로 좁게 확인한다. `not_actionable`은 근거를 triage record에 남긴다.

## 7. Finding 수정 및 검증

Accepted finding을 실제 코드 변경으로 고칠 때는 `fix-finding`을 사용한다. 한 번에 모든 finding을 고치기보다는 하나의 accepted finding을 별도 작업으로 처리하는 것이 리뷰와 검증이 쉽다.

```text
Use $codex-security:fix-finding to fix finding <finding-id> from <report-path>. Validate the issue, make the smallest safe change, add focused regression coverage, and verify that the issue no longer reproduces.
```

가능하면 다음 정보를 함께 제공한다.

- source, sink, attacker input
- impact와 지켜야 하는 security invariant
- 재현 방법 또는 reproducer
- affected files
- validation command

Codex는 부족한 기술 정보는 저장소를 읽어서 보완할 수 있지만, 제품 정책이나 의도한 security invariant는 임의로 추측하게 두지 않는 편이 좋다.

UI에서 수정할 때의 흐름은 다음과 같다.

1. Patch tab에서 `Generate patch`를 눌러 focused patch artifact를 만든다.
2. 변경된 source와 regression test를 모두 읽는다.
3. broad refactor, 무관한 cleanup, 다른 보안 control을 약화하는 변경은 거절한다.
4. diff가 괜찮을 때만 `Apply patch locally`로 working tree에 적용한다.
5. `Verify fix`로 원래 exploit check, regression coverage, 정상 동작, 주변 bypass, 관련 테스트를 실행한다.
6. 검증 결과와 남은 proof gap을 보고 finding을 닫을지 결정한다.

검증이 성공했다고 finding이 자동으로 닫히지는 않는다. 사람이 명령, 결과, 남은 불확실성을 보고 정확한 이유로 닫아야 한다.

CI/CD에서 diff scan과 fix를 한 번에 돌릴 수도 있다.

```text
Use $codex-security:security-diff-scan to review changes from <base-revision> to HEAD. For every finding returned by the scan, use $codex-security:fix-finding to generate and verify a minimal fix. Continue until every finding has either a verified fix or an explicit explanation of why it could not be fixed. Return the scan results, patches, tests, verification commands, and remaining failures.
```

자동 생성된 patch라도 merge는 일반 code review와 release process를 거치는 것이 안전하다.

## 8. Finding export 및 tracking

완료된 Codex Security scan은 두 가지 방식으로 넘길 수 있다.

- Export: JSON, CSV, SARIF 같은 portable artifact 생성
- Track findings: selected finding을 Linear, GitHub, Jira issue 또는 private draft GitHub Security Advisory로 준비

Export는 completed findings workspace에서 `Export`를 선택한 뒤 형식을 고르면 된다.

| 형식 | 용도 |
| --- | --- |
| JSON | sealed structured findings를 도구나 script에서 그대로 사용 |
| CSV | spreadsheet에서 finding과 local triage state 검토 |
| SARIF | SARIF를 지원하는 보안 도구로 전달 |

다른 도구가 전체 scan context를 필요로 한다면 exported findings만 넘기지 말고 `scan-manifest.json`, `findings.json`, `coverage.json`을 함께 보관한다.

Tracking은 `$codex-security:track-findings`를 사용한다. 한 번에 하나의 validated finding 또는 같은 sealed scan에서 명시적으로 선택한 최대 25개 finding을 처리할 수 있다. GitHub Security Advisory draft는 한 번에 하나의 finding만 가능하다. 한 run에서는 provider와 destination을 하나만 사용한다.

Linear 예시는 다음과 같다.

```text
Use $codex-security:track-findings to prepare finding [finding ID] from [completed scan directory] for the Linear team [team] and project [project, if any]. Check for duplicates and show me the exact issue title, body, metadata, and destination. Do not create or update anything until I approve that payload.
```

GitHub issue 예시는 다음과 같다.

```text
Use $codex-security:track-findings to prepare finding [finding ID] from [completed scan directory] for GitHub repository [owner/repository]. Check open and closed issues for duplicates and show me the exact issue title, body, metadata, repository visibility, and authenticated transport. Do not create or update anything until I approve that payload.
```

Jira 예시는 다음과 같다.

```text
Use $codex-security:track-findings to prepare finding [finding ID] from [completed scan directory] for Jira project [project key] as [issue type]. Check for duplicates and show me the exact issue summary, description, metadata, and destination. Do not create or update anything until I approve that payload.
```

중요한 점은 tracking workflow가 바로 쓰기를 수행하지 않는다는 것이다. 먼저 duplicate 상태, issue title/body, metadata, destination을 보여주고 사용자의 승인을 기다린다. destination, visibility, finding set, body가 바뀌면 새 preview를 받아야 한다.

민감한 finding은 private destination으로 보내야 한다. public 또는 internal GitHub repository에 issue를 만들 때는 visibility warning을 확인하고, exploit detail이나 내부 증거, credential 같은 노출되면 안 되는 정보를 제거한 뒤 승인한다. Draft advisory도 나중에 공개될 수 있다는 전제로 내용을 검토해야 한다.
