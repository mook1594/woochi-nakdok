# 핸드오프

> 최신 1개만 유지한다. 이전 내용은 git이 갖고 있다.

**세션 2 — 분할과 매니페스트** · 2026-08-28

## 이 세션에서 한 일

**`analyze`가 완성됐다.** txt를 받아 챕터·청크로 나누고 `.nakdok/manifest.json`을
쓰고 종료 코드 `0`으로 끝난다. 파이프라인 3단계 중 1단계가 끝났다.

## 지금 상태

```
817669b docs: 한국어 문장 분할을 직접 구현으로 확정 (D9)
52522a0 feat(analyze): 청크 분할과 경계 판정 (R3.1~R3.8)
d6d3fb1 docs: 뮤테이션 확인의 함정 두 가지를 검증 프로토콜에 명문화
feb22ff feat(manifest): 매니페스트 생성과 text_hash (R4.1~R4.5, R10.1)
```

| | |
|---|---|
| 테스트 | **70 passed** (`PYTHONDONTWRITEBYTECODE=1 .venv/Scripts/python.exe -m pytest -q -p no:cacheprovider`) |
| 완료 | S2.0, T4, T5, S2.1 |
| 다음 작업 | **T6 — TTS 합성** (R5.1~5.7). **Phase 0 청취가 막고 있다** |

```
nakdok/
  cli.py       analyze 전체 배선 완료. 성공 시 exit 0
  config.py    chapter_pattern · voice · speed
  analyze.py   read_book · split_chapters · split_chunks
  manifest.py  FIELDS(10) · text_hash · build_manifest · load/save
tests/
  test_cli.py  test_analyze.py  test_config.py  test_manifest.py
```

## 실제로 돌려본 결과

임시 디렉토리에 책을 만들어 `nakdok analyze`를 돌린 결과다. 테스트가 아니라 CLI다.

```
1-1  ch1 #1  chapter    '\n'
2-1  ch2 #1  paragraph  '제 1 장  시작\n\n'
2-2  ch2 #2  paragraph  '민수가 말했다. "그래... 알겠어. 정말이야."\n그는 창밖을 봤다.\n\n'
2-3  ch2 #3  scene      '한참이 지났다.\n\n\n'
2-4  ch2 #4  chapter    '장면이 바뀌었다.\n\n'
3-1  ch3 #1  paragraph  '제 2 장  끝\n\n'
3-2  ch3 #2  chapter    '끝이다.\n'
```

- 원문 복원 == 원문 (절대 규칙 1)
- 필드 정확히 10개
- 재실행 후 `audio_path`·`duration_ms` 보존, 청크 하나의 본문을 고치면 **그 청크만** 리셋

## 이 세션에서 정해진 것

| # | 결정 | 근거가 있는 곳 |
|---|---|---|
| 1 | **kss 탈락 → 문장 분할 직접 구현.** 정확도가 아니라 **의존성 무게**로 내렸다 (전이 의존성 25개: pyarrow·scipy·networkx·xlrd==1.2.0…) | `architecture.md` D9 |
| 2 | 챕터 전체가 빈 줄이면 그 빈 줄을 **단독 청크로 남긴다.** 버리면 절대 규칙 1 위반 | `test_all_blank_chapter_preserves_characters` |
| 3 | `id` 형식 = `"{챕터}-{순번}"`, **둘 다 1부터.** R5.5가 실패 로그에 그대로 출력한다 | `test_id_format_is_chapter_dash_order` |
| 4 | 해시 구분자 = `\x00`. 구분자 없이 이으면 `text="가나"+voice="M3"`와 `text="가나M"+voice="3"`이 충돌한다 | `test_hash_avoids_concatenation_collision` |
| 5 | `duration_ms` 초기값 = `null`. `0`으로 두면 실제 0ms 오디오와 구분이 안 된다 | `manifest.py` |
| 6 | `analyze`가 exit **0**을 반환하는 첫 명령이 됐다. `synth`·`build`·`run`은 아직 `1` | `ORCHESTRATION.md` 규약 |

## 이번 세션의 진짜 교훈 — 반려 3건이 전부 같은 뿌리다

T4를 한 번, T5를 한 번 반려했다. **구현은 셋 다 맞았다.** 테스트가 가짜였다.

| 무엇 | 어떻게 가짜였나 |
|---|---|
| R3.2·R3.3 (따옴표·줄임표) | 최종 청크 개수만 봤다. 분할이 틀려도 **바로 다음 병합 단계**가 120자 이하면 도로 합쳐서 결과가 비트 단위로 같다. 분할기를 통째로 무력화해도 통과했다 |
| `id` 형식 | `assert ids == [f"{c['chapter']}-{c['order']}" for c in manifest]` — **기댓값을 검사 대상에서 뽑았다.** 셋이 같이 틀리면 통과한다. 번호를 0부터 매겨도 70개 테스트가 전부 통과했다 |

셋 다 녹색이었고, 요구사항 번호가 붙어 있었고, 코드 리뷰로는 안 잡힌다.
공통 원인은 하나다 — **"이 테스트는 어떤 변경에 실패하는가"를 안 물었다.**

두 규칙이 여기서 나왔다 (`ORCHESTRATION.md` 검증 프로토콜):

1. 정보를 줄이는 단계(병합·정규화·해싱·직렬화) **뒤에서** 그 앞 단계를 검증하지 않는다
2. 기댓값은 **리터럴로 적는다.** 단언의 오른쪽이 왼쪽 객체를 참조하면 항등식이다

## 함정

1. **`PYTHONDONTWRITEBYTECODE=1`을 세션 내내 걸어라.** 명령 블록마다 거는 것으로는
   부족하다 — 이번에 뮤테이션을 되돌린 뒤 CLI를 직접 돌렸다가 **뮤테이션된 바이트코드가
   실행돼** 챕터 번호가 0부터 나왔다. 소스는 멀쩡했고 `diff`도 비어 있었다.
   `>= 2` → `>= 3`처럼 **크기가 같은** 편집을 같은 초에 되돌리면 `.pyc` 무효화 판정
   `(mtime 초, 크기)`이 속는다. 이상하면 `__pycache__`부터 지운다
2. **가상환경이 자동 활성화되지 않는다.** 항상 `.venv/Scripts/python.exe`
3. **콘솔이 cp1252다.** `PYTHONIOENCODING=utf-8`. `cli.py`는 `main()`에서 우회한다
4. **Git Bash의 `/tmp`를 파이썬에 그대로 넘기지 마라.** `\tmp\...`로 해석돼 깨진다.
   `cygpath -w "$TEMP"`를 쓴다
5. **보이스를 바꾸면 책 전체가 재합성된다.** Phase 0 확정 전 본격 합성 금지
6. git 신원은 이 리포에서 `mook1594`, 원격은 ssh alias `github-mook`
7. **PR을 넘긴 뒤에 커밋하지 마라**

## 미해소 / 사람 대기

| 항목 | 상태 |
|---|---|
| **Phase 0 청취** | **이제 T6를 실제로 막는다.** 보이스 1종 + `speed` 확정 전에는 합성을 시작할 수 없다 |
| **빈 줄로만 된 청크** | 실증됨 — 위 실행 결과의 `1-1` (`text = '\n'`). 지금은 다른 청크와 똑같이 매니페스트에 들어가고, T6가 그대로 TTS에 넘긴다. **요구사항에 규정이 없다.** T6 전에 결정해야 한다 |
| R6.2의 `chapter` 1000ms | `scene` 1800ms보다 짧다. 의도 미확인. Phase 1 청취에서 조정 |
| 테스트 로케일 의존 | `test_missing_file_reports_cause`가 OS 영문 메시지에 의존한다 |

## 다음 세션 첫 걸음

1. `ORCHESTRATION.md`의 **세션 시작 절차**를 실행한다 — 특히 전제 감사
2. **Phase 0 청취가 끝났는지 먼저 확인한다.** 안 끝났으면 T6를 시작하지 않는다
3. 빈 줄 청크를 어떻게 할지 `requirements.md`에 항목으로 올리고 승인을 받는다
