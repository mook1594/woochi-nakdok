# CLAUDE.md

## 프로젝트

`nakdok` — 한국어 txt 전자책을 로컬 TTS로 낭독해 챕터 메타데이터가 포함된 m4b 오디오북으로 변환하는 CLI.

전부 로컬에서 돈다. 클라우드 API 호출 없음.

## 현재 단계

**Phase 1** (단일 보이스 파이프라인). 상세는 `docs/roadmap.md`.

Phase 1이 끝나기 전에는 화자 캐스팅, DB, 웹 UI 관련 코드를 작성하지 않는다.
구조만 열어두고 구현은 미룬다.

## 스택

| 역할 | 선택 | 비고 |
|---|---|---|
| 오케스트레이터 | Python 3.13 CLI | 파이프라인 전체를 여기서 제어 |
| TTS | Supertonic 3 (ONNX) | `supertonic` 패키지를 라이브러리로 직접 사용 |
| 한국어 문장 분할 | kss (**후보, 미확정**) | T4에서 실측 후 확정. `docs/architecture.md` D9 |
| LLM | llama-server (Qwen3-35B-A3B, IQ4_XS) | Phase 3에서만. Phase 1~2는 호출 안 함 |
| 오디오 결합 | ffmpeg | concat + 챕터 메타 + AAC 인코딩 |

TTS는 사이드카 프로세스 없이 `from supertonic import TTS`로 인프로세스 호출한다.
HTTP 서버(`supertonic serve`)도 패키지에 들어 있지만 쓰지 않는다 — 같은 프로세스
안에서 함수로 부를 수 있는데 포트·헬스체크·재시도를 끼워 넣을 이유가 없다.

## 명령

```
nakdok analyze <book.txt>   # 챕터/청크 분할 → .nakdok/manifest.json
nakdok synth                # manifest 기준, 해시가 바뀐 청크만 합성
nakdok build                # ffmpeg concat → <book>.m4b
nakdok run <book.txt>       # analyze → synth → build
```

각 단계는 독립 실행 가능해야 한다. `synth`를 두 번 돌리면 두 번째는 아무것도
합성하지 않고 즉시 끝나야 한다.

## 작업 디렉토리 구조

```
<book>.txt
<book>.m4b                  # 최종 산출물
.nakdok/
  manifest.json             # 청크 목록 (SSOT)
  lexicon.yaml              # 치환 사전 (사람이 편집, Phase 2)
  cast.yaml                 # 캐스팅 시트 (사람이 편집, Phase 3)
  audio/<sha256[:16]>.wav   # 청크별 합성 결과 캐시
```

`manifest.json`이 파이프라인의 단일 진실 공급원(SSOT)이다. 각 청크는
`{ id, chapter, order, boundary_after, text, text_hash, voice, speed, audio_path, duration_ms }`를
갖는다.

`boundary_after`는 이 청크와 다음 청크 사이의 경계 종류(`sentence` `paragraph`
`scene` `chapter`)다. 원문의 줄바꿈 구조는 `analyze`만 볼 수 있으므로, 여기에
기록해 두지 않으면 `build`가 무음 길이를 고를 수 없다. 이 필드가 `build`를 원문
파일로부터 독립시킨다.

## 절대 규칙

1. **원문을 변형하지 않는다.** 정규화는 TTS에 넘기는 문자열에만 적용하고,
   `manifest.json`의 `text` 필드에는 원문을 그대로 보존한다. 사용자가 원문과
   낭독 결과를 대조할 수 있어야 한다.

2. **LLM 출력은 구조화된 JSON만 받는다.** 본문 텍스트를 LLM이 생성해서
   돌려주게 하는 코드는 작성하지 않는다. 매핑(토큰→읽는법, 인덱스→화자)만 받는다.

3. **wav를 최종 산출물로 남기지 않는다.** 24kHz/16bit mono 기준 시간당 약 170MB다.
   `.nakdok/audio/`의 wav는 중간 캐시이고, 최종 m4b는 AAC 48kbps mono로 인코딩한다.

4. **합성은 항상 텍스트 해시로 캐싱한다.** 해시가 같으면 재합성하지 않는다.
   이게 깨지면 문단 하나 고칠 때마다 책 전체를 다시 돌리게 된다.

5. **무음 삽입은 코드가 담당한다.** TTS가 문단·장면 전환의 쉼을 만들어주지 않는다.
   기본값은 `docs/architecture.md`의 무음 정책 표를 따르고, 설정으로 노출한다.

## 하지 말 것

- **문장 단위로 잘라 합성하지 않는다.** 문장마다 끊으면 운율이 리셋돼서 톤이
  뚝뚝 끊긴다. 한국어는 `max_chunk_length`가 자동 120자이므로 그 근처를 목표로
  문장 경계에 맞춰 묶는다.
- **화자 판별을 규칙 없이 LLM에 통째로 맡기지 않는다.** 명시적 지문(`~라고 X가
  말했다`)을 규칙으로 먼저 확정하고, 남은 것만 LLM에 넘긴다. 순서가 반대면
  정확도와 비용이 둘 다 나빠진다.
- **자체 오디오 플레이어를 만들지 않는다.** m4b로 뽑으면 기존 오디오북 앱이
  재생위치 기억·배속·슬립타이머를 전부 처리한다.
- **커스텀 보이스(Voice Builder) 경로를 전제하지 않는다.** 해당 서비스는
  2026-08-31 종료됐다. 내장 보이스 M1–M5 / F1–F5 10종이 전부다.

## 검증

파이프라인의 최종 품질은 자동 테스트로 판정할 수 없다. **사람이 귀로 듣는다.**

자동화 가능한 것과 아닌 것을 구분한다:

- 자동 테스트 대상: 챕터 분할, 청크 분할, 해시 캐싱, manifest 스키마,
  duration 합계와 m4b 길이 일치, 재실행 시 no-op
- 사람이 판정: 낭독 톤, 쉼의 길이, 오독 여부, 화자 배분의 자연스러움

에이전트는 후자를 "테스트 통과"로 보고하지 않는다. 대신 사람이 들어볼 수 있는
샘플(챕터 1개)을 만들어 놓고 판단을 요청한다.

## 커밋 / 작업 단위

- 하나의 커밋 = `docs/requirements.md`의 요구사항 하나. 커밋 메시지에 ID를 남긴다
  (예: `feat: 챕터 분할 (R2.1, R2.2)`).
- 요구사항에 없는 기능을 임의로 추가하지 않는다. 필요하다고 판단되면
  `requirements.md`에 항목을 제안하고 승인을 받은 뒤 구현한다.

## 참고 문서

- `docs/requirements.md` — EARS 요구사항 (구현 기준)
- `docs/architecture.md` — 파이프라인 설계와 결정 근거
- `docs/roadmap.md` — 단계별 계획과 종료 조건
