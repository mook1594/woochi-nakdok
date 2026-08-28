# 핸드오프

> 최신 1개만 유지한다. 이전 내용은 git이 갖고 있다.

**세션 1 — 스캐폴딩과 입력** · 2026-08-28

## 이 세션에서 한 일

**코드가 생겼다.** 패키지 뼈대, CLI 4개 명령, 입력 디코딩, 챕터 분할까지.
`analyze`가 실제 책 파일을 읽고 챕터를 나눠 보고한다. 매니페스트(T5)가 없어
아직 종료 코드 1로 끝난다.

## 지금 상태

```
058f79b docs: 세션 종료 절차에 푸시 확인 단계 추가        (세션 0 이월)
eb75e30 feat(cli): 4개 서브커맨드 파서와 진입점 (T1)
5817026 feat(analyze): 입력 파일 인코딩 감지 (R1.1~R1.4)
1125dee feat(analyze): 챕터 분할과 설정 로딩 (R2.1~R2.5)
294eeee test(analyze): 파일 접근 실패를 R1.5로 명세화 (R1.5)
```

| | |
|---|---|
| 테스트 | **38 passed** (`.venv/Scripts/python.exe -m pytest`) |
| 완료 | S1.0, T1, T2, T2.1, T3 |
| 다음 작업 | **T4 — 청크 분할 + `boundary_after`** (R3.1~3.8) |

```
nakdok/
  cli.py       argparse 4개 서브커맨드, analyze 경로에 디코딩 연결
  config.py    .nakdok/config.yaml 로딩. 지금은 chapter_pattern만 읽는다
  analyze.py   read_book() 디코딩 · split_chapters() 챕터 분할
tests/
  test_cli.py  test_analyze.py  test_config.py
```

## 종료 코드 (T4가 반드시 지킬 것)

규약 전문은 `ORCHESTRATION.md`의 **규약** 절에 있다. 요약: `2`=입력 오류,
`1`=미구현, `0`=성공. **현재 어느 명령도 `0`을 반환하지 않는다.**

T4에서 청크 분할만 붙이고 `analyze`를 `0`으로 바꾸지 마라 — 매니페스트(T5)가
없으면 `analyze`는 미완이다.

## 이 세션에서 정해진 것

| # | 결정 | 근거가 있는 곳 |
|---|---|---|
| 1 | **R1.5 신설** — 파일 접근 실패도 종료 코드 2 | `requirements.md` R1.5 |
| 2 | 챕터 경계 줄은 **그 챕터의 첫 줄**로 들어간다 | `test_boundary_line_starts_its_chapter` |
| 3 | 첫 경계 앞 텍스트(제목·서문)는 **별도 챕터로 보존**한다. 버리면 절대 규칙 1 위반 | `test_split_preserves_every_character` |
| 4 | `config.yaml`의 `chapter_pattern`은 기본 3종을 **대체**한다 (추가가 아니다) | `test_config_pattern_replaces_defaults` |
| 5 | 설정은 **책 파일 옆** `.nakdok/`에서 읽는다. cwd가 아니다 | `test_config_read_next_to_book_not_cwd` |

## R1.5가 생긴 경위 (같은 실수를 막기 위해)

T2에서 에이전트가 `cli.py`에 `OSError` 처리를 요구사항 근거 없이 넣었다.
스코프 위반으로 보고 걷어내려다 뮤테이션을 걸어보니, **T1의 기존 테스트를
지탱하는 코드**였다 — `analyze`가 파일을 읽기 시작하면서 존재하지 않는
`book.txt`를 실제로 열게 됐기 때문이다.

즉 스코프 위반이 아니라 **미명세**였다. 코드를 걷어내는 대신 R1.5를 추가해
명세와 코드를 일치시켰다. 구현은 한 줄도 바뀌지 않았다.

교훈: 요구사항 밖 코드를 발견하면 지우기 전에 **뮤테이션으로 그게 무엇을
지탱하는지 먼저 확인한다.** 지우고 나서 알면 늦다.

## 함정 (세션 0에서 이월, 여전히 유효)

1. **가상환경이 자동 활성화되지 않는다.** 항상 `.venv/Scripts/python.exe`
2. **콘솔이 cp1252다.** 한글 출력 스크립트에 `PYTHONIOENCODING=utf-8`.
   `cli.py`는 `main()`에서 stdout/stderr를 UTF-8로 재설정해 이걸 우회한다
3. **보이스를 바꾸면 책 전체가 재합성된다.** Phase 0 확정 전 본격 합성 금지
4. git 신원은 이 리포에서 `mook1594`, 원격은 ssh alias `github-mook`
5. **PR을 넘긴 뒤에 커밋하지 마라.** 세션 0에서 두 번 어겨 PR을 두 개 만들었다.
   `ORCHESTRATION.md` 세션 종료 절차 4번

## 미해소 / 사람 대기

| 항목 | 상태 |
|---|---|
| **Phase 0 청취** | Ben이 직접 들어야 한다. **T6를 막고 있다.** T4·T5는 이것 없이 진행 가능 |
| kss 채택 여부 | **T4에서 판정.** `architecture.md` D9 — 테스트를 먼저 쓰고 kss를 붙여 통과 여부를 본다. 순서를 뒤집지 마라 |
| R6.2의 `chapter` 1000ms | `scene` 1800ms보다 짧다. 의도 미확인. Phase 1 청취에서 조정 |
| 테스트 로케일 의존 | `test_missing_file_reports_cause`가 OS 영문 메시지(`No such file`)에 의존한다. 다른 로케일에서 깨질 수 있다 |

## 다음 세션 첫 걸음

1. `ORCHESTRATION.md`의 **세션 시작 절차**를 실행한다 — 특히 전제 감사
2. T4 임무서를 `nakdok-implementer`에게 넘긴다. **테스트 먼저, kss는 그다음**
