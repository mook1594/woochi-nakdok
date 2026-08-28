# 핸드오프

> 최신 1개만 유지한다. 이전 내용은 git이 갖고 있다.

**세션 0 — 규칙 정립** · 2026-08-28

## 이 세션에서 한 일

문서만 고쳤다. **코드는 아직 0줄이다.**

프로젝트 언어를 .NET에서 **Python으로 바꿨고**, 그 결과 파생된 설계 변경을 문서
전체에 반영했다. 그리고 미해소 상태로 남아 있던 설계 결정 3개를 닫았다.

## 지금 상태

```
eff8eec chore: .gitignore 추가
d72092a docs: 프로젝트 문서 초기화
749f229 docs: 무음 경계 종류를 매니페스트 필드로 승격
bf3d413 docs: 설정 파일을 .nakdok/config.yaml로 확정
ca801e9 docs: 단일 보이스와 speed의 출처를 R4.5로 정의
```

| | |
|---|---|
| 개발 환경 | `.venv` (Python 3.13.14). supertonic 1.3.1 import 검증됨 |
| 코드 | 없음 |
| 다음 작업 | **T1 — 패키지 스캐폴딩 + CLI** (`ORCHESTRATION.md` 참조) |

## 이 세션에서 정해진 것

| # | 결정 | 근거가 있는 곳 |
|---|---|---|
| 1 | 오케스트레이터 언어 = **Python**. supertonic을 사이드카 없이 `import`로 직접 호출 | `architecture.md` D4 |
| 2 | 재시도 요구사항(구 R5.5) **삭제**. 인프로세스 함수 호출에는 회복할 네트워크 실패가 없다 | `architecture.md` D4 |
| 3 | 청크에 **`boundary_after`** 필드 추가 (10필드). 무음 경계 판정은 `analyze`가 하고 `build`는 읽기만 한다 | `architecture.md` D6, R3.7·R3.8 |
| 4 | 설정 파일 = **`.nakdok/config.yaml`**. 없으면 코드 기본값 | R2.3, R6.3 |
| 5 | 단일 보이스·speed의 출처 = config, 기본값 **`M3` / `0.95`** (자리표시자) | R4.5 |
| 6 | 한국어 문장 분할 라이브러리(kss)는 **미확정**. T4에서 테스트를 먼저 쓰고 판정 | `architecture.md` D9 |
| 7 | **전이 의존성에 기대지 않는다.** CLI는 `argparse`(= `click` 배제), `pyyaml`은 `pyproject.toml`에 직접 선언 | `ORCHESTRATION.md` T1 · 모듈 배치 |

## 실측으로 확인한 것

supertonic 1.3.1 휠을 직접 열어 본 결과다. 문서의 주장 중 틀린 것이 있었다.

- `from supertonic import TTS` — 라이브러리 API 존재 ✅
- `DEFAULT_MAX_CHUNK_LENGTH_KO = 120` — D5의 근거가 실제 상수로 존재 ✅
- `speed` 0.7~2.0 기본 1.05 / `total_steps` 기본 8 최대 100
- `auto_download=True`가 기본 — 모델 가중치 내려받기 절차가 따로 필요 없다
- `duration`은 반환 wav 배열 길이로 계산한다. **ffprobe 불필요**
- **onnxruntime 프로바이더가 CPU뿐이다** (`AzureExecutionProvider`, `CPUExecutionProvider`).
  RTX 4060은 쓰이지 않는다. Phase 0에서 RTF를 잴 때 이 조건을 기억할 것
- ~~"C#/.NET SDK 공식 지원"~~ — 검증되지 않아 D3에서 삭제
- ~~"Steno에서 whisper-server를 붙인 패턴 재사용"~~ — woochi-steno는 앱 코드 0줄.
  재사용할 대상이 없어 D4에서 삭제

## 함정 (다음 세션이 밟기 쉬운 것)

1. **가상환경이 자동 활성화되지 않는다.** 항상 `.venv/Scripts/python.exe`로 부른다
2. **콘솔이 cp1252다.** 한글을 출력하는 스크립트는 `PYTHONIOENCODING=utf-8` 없이
   크래시한다
3. **보이스를 바꾸면 책 전체가 재합성된다** (`text_hash`가 voice·speed를 포함).
   Phase 0으로 보이스를 확정하기 전에 본격 합성을 시작하지 않는다
4. git 신원이 이 리포에서 `mook1594 / wjdanr89@gmail.com`으로 지역 설정돼 있다.
   원격은 ssh alias `github-mook`을 쓴다

## 미해소 / 사람 대기

| 항목 | 상태 |
|---|---|
| **Phase 0 청취** | Ben이 직접 들어야 한다. **T6를 막고 있다.** T1~T5는 이것 없이 진행 가능 |
| R6.2의 `chapter` 1000ms | `scene` 1800ms보다 **짧다.** 의도인지 미확인. 원문 유지 중 — Phase 1 청취에서 조정 |
| `TTS()` 생성 실패 | 요구사항 어디에도 없다. 지금은 예외가 그대로 올라가 `synth`가 죽는다. 그대로 두기로 했다 |
| 요구사항 ID | R5·R6를 한 번씩 재번호했다. **T1부터 고정.** 더 이상 당기지 않는다 |

## 다음 세션 첫 걸음

1. `ORCHESTRATION.md`의 **세션 시작 절차**를 실행한다 — 특히 전제 감사
2. T1 임무서를 `nakdok-implementer`에게 넘긴다
