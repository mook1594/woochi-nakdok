# Requirements: nakdok

## Introduction

`nakdok`은 한국어 txt 전자책을 로컬 TTS로 낭독해 챕터 메타데이터가 포함된 m4b
오디오북 파일로 변환하는 CLI다. 클라우드 API 없이 전량 로컬에서 처리하며, 텍스트
일부를 수정했을 때 해당 구간만 재합성하는 증분 처리를 지원한다.

## Glossary

- **청크(Chunk)**: TTS에 한 번에 넘기는 텍스트 단위. 문장 경계에 맞춰 묶되 한국어 기준 120자를 목표로 한다.
- **세그먼트(Segment)**: 화자가 동일한 연속 텍스트 구간. 내레이션 또는 하나의 대화문.
- **매니페스트(Manifest)**: 청크 목록과 각 청크의 메타데이터를 담은 `.nakdok/manifest.json`. 파이프라인의 SSOT.
- **텍스트 해시**: 청크의 정규화 후 문자열 + 보이스 + 속도를 결합해 계산한 SHA-256 값. 캐시 키로 쓴다.
- **치환 사전(Lexicon)**: 고유명사·한자어 등의 읽는 법을 사람이 정의한 `.nakdok/lexicon.yaml`.
- **캐스팅 시트(Cast sheet)**: 화자별 보이스 배정과 수동 교정을 담은 `.nakdok/cast.yaml`.
- **보이스**: Supertonic 내장 보이스 스타일 식별자. M1–M5, F1–F5 10종.
- **무음 정책**: 경계 종류(문장/문단/장면/챕터)별 삽입 무음 길이 설정.
- **미확정 화자(unknown)**: 화자 판별이 실패한 대화문에 부여하는 예약 화자명.

---

## Requirements

### Requirement 1: 입력 검증

**User story:** 독자로서, 잘못된 입력 파일을 넘겼을 때 즉시 원인을 알고 싶다. 몇 시간짜리 합성이 끝난 뒤에 실패를 발견하고 싶지 않기 때문이다.

**Acceptance criteria:**

1.1. WHEN `analyze` 명령이 실행되면, THE SYSTEM SHALL 입력 파일을 UTF-8로 디코딩한다.

1.2. IF 입력 파일이 UTF-8로 디코딩되지 않으면, THEN THE SYSTEM SHALL CP949로 재시도하고, 성공 시 감지된 인코딩을 표준 출력에 보고한다.

1.3. IF 입력 파일이 UTF-8과 CP949 모두로 디코딩되지 않으면, THEN THE SYSTEM SHALL 종료 코드 2와 함께 실패한 인코딩 목록을 출력하고 중단한다.

1.4. IF 입력 파일의 문자 수가 0이면, THEN THE SYSTEM SHALL 종료 코드 2와 함께 중단한다.

---

### Requirement 2: 챕터 분할

**User story:** 독자로서, 생성된 오디오북에서 챕터 단위로 이동하고 싶다. 이어듣기와 되감기의 기본 단위이기 때문이다.

**Acceptance criteria:**

2.1. WHEN `analyze` 명령이 실행되면, THE SYSTEM SHALL 설정된 챕터 경계 정규식에 일치하는 줄을 챕터 시작점으로 표시한다.

2.2. THE SYSTEM SHALL 기본 챕터 경계 정규식으로 `제\s*\d+\s*[장화부]`, `^\d+\.?\s*$`, `^[Cc]hapter\s+\d+`를 사용한다.

2.3. WHERE 설정 파일에 `chapter_pattern`이 지정된 경우, THE SYSTEM SHALL 기본 정규식 대신 지정된 정규식을 사용한다.

2.4. IF 챕터 경계가 하나도 검출되지 않으면, THEN THE SYSTEM SHALL 전체 텍스트를 단일 챕터로 처리하고 경고를 출력한다.

2.5. WHEN 챕터 분할이 완료되면, THE SYSTEM SHALL 검출된 챕터 수와 각 챕터의 문자 수를 표준 출력에 보고한다.

---

### Requirement 3: 청크 분할

**User story:** 독자로서, 낭독의 호흡이 문장 중간에서 끊기지 않기를 원한다. 어색한 절단이 몰입을 깨기 때문이다.

**Acceptance criteria:**

3.1. WHEN 챕터 분할이 완료되면, THE SYSTEM SHALL 각 챕터의 텍스트를 문장 경계에서 분할한다.

3.2. THE SYSTEM SHALL 문장 경계 판정 시 따옴표(`"`, `'`, `「」`) 내부의 마침표를 경계로 취급하지 않는다.

3.3. THE SYSTEM SHALL 줄임표(`…`, `...`)를 문장 경계로 취급하지 않는다.

3.4. WHEN 문장 분할이 완료되면, THE SYSTEM SHALL 연속된 문장을 누적 길이 120자를 초과하지 않는 범위에서 하나의 청크로 묶는다.

3.5. IF 단일 문장의 길이가 120자를 초과하면, THEN THE SYSTEM SHALL 해당 문장을 단독 청크로 배정한다.

3.6. THE SYSTEM SHALL 청크가 문단 경계를 넘어 병합되지 않도록 문단 경계에서 청크를 종료한다.

3.7. WHEN 청크 분할이 완료되면, THE SYSTEM SHALL 각 청크와 다음 청크 사이의 경계를 다음 우선순위로 판정한다: 챕터가 바뀌면 `chapter`, 빈 줄이 2개 이상 연속되면 `scene`, 문단이 바뀌면 `paragraph`, 그 외에는 `sentence`.

3.8. THE SYSTEM SHALL 전체 텍스트의 마지막 청크의 경계를 `chapter`로 판정한다.

---

### Requirement 4: 매니페스트 생성

**User story:** 개발자로서, 파이프라인의 중간 상태를 파일로 검사하고 싶다. 어느 단계에서 문제가 생겼는지 추적해야 하기 때문이다.

**Acceptance criteria:**

4.1. WHEN `analyze` 명령이 완료되면, THE SYSTEM SHALL `.nakdok/manifest.json`을 생성한다.

4.2. THE SYSTEM SHALL 각 청크에 대해 `id`, `chapter`, `order`, `boundary_after`, `text`, `text_hash`, `voice`, `speed`, `audio_path`, `duration_ms` 필드를 매니페스트에 기록한다.

4.3. THE SYSTEM SHALL 매니페스트의 `text` 필드에 원문 문자열을 변형 없이 기록한다.

4.4. WHEN `analyze` 명령이 기존 매니페스트가 있는 상태에서 실행되면, THE SYSTEM SHALL 기존 청크 중 `text_hash`가 동일한 항목의 `audio_path`와 `duration_ms`를 보존한다.

---

### Requirement 5: 음성 합성

**User story:** 독자로서, 텍스트가 사람 목소리로 낭독되기를 원한다. 이것이 이 도구의 목적이기 때문이다.

**Acceptance criteria:**

5.1. WHEN `synth` 명령이 실행되면, THE SYSTEM SHALL 매니페스트의 각 청크에 대해 `audio_path`가 가리키는 파일의 존재 여부를 확인한다.

5.2. IF 청크의 `audio_path`가 비어 있거나 해당 파일이 존재하지 않으면, THEN THE SYSTEM SHALL 해당 청크를 TTS 엔진으로 합성한다.

5.3. WHEN 청크 합성이 성공하면, THE SYSTEM SHALL 결과를 `.nakdok/audio/<text_hash>.wav`로 저장하고, 반환된 파형의 샘플 수와 샘플레이트로 `duration_ms`를 계산해 매니페스트의 `audio_path`와 `duration_ms`를 갱신한다.

5.4. THE SYSTEM SHALL TTS 엔진 호출에 `voice`에 대응하는 보이스 스타일, `speed`, `lang="ko"`를 전달한다.

5.5. IF 청크 합성이 예외로 실패하면, THEN THE SYSTEM SHALL 해당 청크의 `id`와 오류 내용을 기록하고 다음 청크로 진행한다.

5.6. WHEN `synth` 명령이 완료되면, THE SYSTEM SHALL 합성한 청크 수, 캐시로 건너뛴 청크 수, 실패한 청크 수를 보고한다.

5.7. IF 실패한 청크가 1개 이상이면, THEN THE SYSTEM SHALL 종료 코드 1로 종료한다.

---

### Requirement 6: 무음 삽입

**User story:** 독자로서, 문단과 장면 사이에서 충분히 쉬는 낭독을 원한다. 쉼이 짧으면 듣기가 숨 막히기 때문이다.

**Acceptance criteria:**

6.1. WHEN `build` 명령이 실행되면, THE SYSTEM SHALL 인접한 두 청크 사이에 앞 청크의 `boundary_after`에 대응하는 무음을 삽입한다.

6.2. THE SYSTEM SHALL 기본 무음 길이로 `sentence` 400ms, `paragraph` 800ms, `scene` 1800ms, `chapter` 1000ms를 사용한다.

6.3. WHERE 설정 파일에 무음 정책이 지정된 경우, THE SYSTEM SHALL 기본값 대신 지정된 값을 사용한다.

---

### Requirement 7: m4b 출력

**User story:** 독자로서, 결과물을 기존 오디오북 앱에서 챕터 이동과 함께 재생하고 싶다. 전용 플레이어를 따로 쓰고 싶지 않기 때문이다.

**Acceptance criteria:**

7.1. WHEN `build` 명령이 실행되면, THE SYSTEM SHALL 모든 청크 오디오와 무음을 매니페스트의 `chapter`·`order` 순서대로 결합한다.

7.2. THE SYSTEM SHALL 결합된 오디오를 AAC 48kbps 모노로 인코딩해 `<입력파일명>.m4b`로 출력한다.

7.3. THE SYSTEM SHALL 각 챕터의 시작 시각을 m4b 챕터 메타데이터로 기록한다.

7.4. THE SYSTEM SHALL 입력 파일명을 m4b의 제목 태그로 기록한다.

7.5. IF 매니페스트에 `audio_path`가 비어 있는 청크가 존재하면, THEN THE SYSTEM SHALL 종료 코드 1과 함께 해당 청크 목록을 출력하고 m4b를 생성하지 않는다.

---

### Requirement 8: 치환 사전 (Phase 2)

**User story:** 독자로서, TTS가 잘못 읽는 고유명사를 고칠 수 있기를 원한다. 같은 오독이 책 전체에서 반복되기 때문이다.

**Acceptance criteria:**

8.1. WHERE `.nakdok/lexicon.yaml`이 존재하는 경우, WHEN 청크를 TTS에 전송하면, THE SYSTEM SHALL 사전에 정의된 표기를 대응하는 읽는 법으로 치환한 문자열을 전송한다.

8.2. THE SYSTEM SHALL 치환된 문자열을 기준으로 `text_hash`를 계산한다.

8.3. THE SYSTEM SHALL 매니페스트의 `text` 필드에는 치환 전 원문을 유지한다.

8.4. WHEN `analyze` 명령이 실행되면, THE SYSTEM SHALL 사전에 등재되지 않은 한자·로마자 토큰 목록을 `.nakdok/lexicon.candidates.yaml`로 출력한다.

---

### Requirement 9: 화자 판별 (Phase 3)

**User story:** 독자로서, 대화문이 내레이션과 다른 목소리로 들리기를 원한다. 소설의 대화가 구분되면 몰입이 깊어지기 때문이다.

**Acceptance criteria:**

9.1. WHEN `cast` 명령이 실행되면, THE SYSTEM SHALL 따옴표로 감싸인 구간을 대화 세그먼트로, 나머지를 내레이션 세그먼트로 분류한다.

9.2. WHEN 대화 세그먼트 분류가 완료되면, THE SYSTEM SHALL 인접한 지문에서 발화 동사 패턴(`말했다`, `물었다`, `소리쳤다`, `대답했다`)과 결합된 인명을 추출해 해당 세그먼트의 화자로 확정한다.

9.3. WHEN 규칙 기반 화자 확정이 완료되면, THE SYSTEM SHALL 확정된 인명 목록을 등장인물 후보로 수집한다.

9.4. WHERE LLM 엔드포인트가 설정된 경우, THE SYSTEM SHALL 화자가 미확정인 세그먼트를 챕터 단위로 묶어 등장인물 후보 목록과 함께 LLM에 전송한다.

9.5. THE SYSTEM SHALL LLM 응답으로 `{세그먼트 id: 화자명}` 형태의 JSON만 수용하고, 후보 목록·`narrator`·`unknown` 이외의 화자명을 포함한 항목은 `unknown`으로 대체한다.

9.6. WHEN 화자 판별이 완료되면, THE SYSTEM SHALL 화자별 보이스 배정을 담은 `.nakdok/cast.yaml`을 생성한다.

9.7. WHERE `cast.yaml`에 `overrides` 항목이 존재하는 경우, THE SYSTEM SHALL 해당 세그먼트의 화자를 LLM 판정보다 우선해 지정된 값으로 확정한다.

9.8. IF 화자가 `unknown`인 세그먼트가 존재하면, THEN THE SYSTEM SHALL 해당 세그먼트에 내레이터 보이스를 배정한다.

9.9. WHEN `cast` 명령이 완료되면, THE SYSTEM SHALL 전체 대화 세그먼트 수, 규칙으로 확정된 수, LLM으로 확정된 수, `unknown`으로 남은 수를 보고한다.

---

### Requirement 10: 증분 재생성

**User story:** 독자로서, 사전이나 캐스팅을 수정한 뒤 바뀐 부분만 다시 합성하고 싶다. 매번 전체를 다시 돌리면 수정 자체가 비현실적이기 때문이다.

**Acceptance criteria:**

10.1. THE SYSTEM SHALL 청크의 `text_hash`를 치환 후 텍스트, `voice`, `speed`를 결합해 계산한다.

10.2. WHEN `synth` 명령이 실행되면, THE SYSTEM SHALL `text_hash`에 해당하는 오디오 파일이 존재하는 청크를 합성 대상에서 제외한다.

10.3. WHEN 변경 사항이 없는 상태로 `synth` 명령이 실행되면, THE SYSTEM SHALL TTS 엔진을 호출하지 않고 종료한다.

10.4. WHEN `synth` 명령이 완료되면, THE SYSTEM SHALL 매니페스트의 어느 청크에서도 참조되지 않는 `.nakdok/audio/` 내 파일 목록을 보고한다.
