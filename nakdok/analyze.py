"""입력 파일 디코딩, 챕터 분할, 청크 분할. 매니페스트 생성은 T5 이후에 붙인다."""

import re
from pathlib import Path

# 시도 순서. R1.3의 "실패한 인코딩 목록"도 이 순서를 그대로 쓴다.
ENCODINGS = ("utf-8", "cp949")

# Supertonic 3의 한국어 청크 상한 실측값(DEFAULT_MAX_CHUNK_LENGTH_KO, architecture.md D5).
# 이보다 크게 묶어도 TTS 내부에서 다시 잘리고, 그 재분할 지점의 무음은 코드가 제어하지 못한다.
MAX_CHUNK_CHARS_KO = 120

# R3.2 — 따옴표 내부 문장부호는 경계로 보지 않는다. 여는/닫는 문자가 다른 「」는 별도 매핑.
_QUOTE_PAIRS = {'"': '"', "'": "'", "「": "」"}
_SENTENCE_END = ".!?"


class InputError(Exception):
    """입력 파일을 읽을 수 없다. 호출자는 종료 코드 2로 끝낸다."""


def read_book(path: str | Path) -> str:
    """원문을 그대로 돌려준다. 정규화도 BOM 제거도 하지 않는다."""
    data = Path(path).read_bytes()
    for enc in ENCODINGS:
        try:
            text = data.decode(enc)
        except UnicodeDecodeError:
            continue
        if enc != ENCODINGS[0]:
            print(f"인코딩 감지: {enc}")  # R1.2 — 폴백으로 읽었을 때만 보고한다
        if not text:
            raise InputError("입력 파일의 문자 수가 0이다")
        return text
    raise InputError(f"디코딩 실패: {', '.join(ENCODINGS)}")


def split_chapters(text: str, patterns: tuple[str, ...]) -> list[str]:
    """경계 줄을 챕터 시작점으로 삼아 나눈다. 문자를 더하거나 빼지 않는다."""
    regexes = [re.compile(p) for p in patterns]
    chapters: list[str] = []
    current: list[str] = []
    found = 0

    for line in text.splitlines(keepends=True):
        if any(r.search(line) for r in regexes):  # R2.1 — 줄 단위로 매칭한다
            found += 1
            if current:  # 첫 경계 앞의 텍스트도 하나의 챕터로 남긴다
                chapters.append("".join(current))
                current = []
        current.append(line)
    chapters.append("".join(current))

    if found == 0:
        print("경고: 챕터 경계를 찾지 못했다. 전체를 단일 챕터로 처리한다")  # R2.4
    print(f"챕터 {len(chapters)}개")  # R2.5
    for i, chapter in enumerate(chapters, 1):
        print(f"  챕터 {i}: {len(chapter)}자")
    return chapters


def _split_sentences(text: str) -> list[str]:
    """문장 경계에서 자른다. R3.2 — 따옴표(`"` `'` `「」`) 내부, R3.3 — 줄임표(`…` `...`)는
    경계로 보지 않는다. 슬라이스만 이어붙이므로 문자를 잃지 않는다."""
    sentences: list[str] = []
    start = 0
    stack: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if stack and ch == stack[-1]:
            stack.pop()
            i += 1
        elif not stack and ch in _QUOTE_PAIRS:
            stack.append(_QUOTE_PAIRS[ch])
            i += 1
        elif stack:
            i += 1  # 따옴표 안 — 문장부호를 봐도 경계로 취급하지 않는다
        elif ch == "…" or text[i : i + 3] == "...":
            i += 1 if ch == "…" else 3  # 줄임표 통째로 건너뛴다 (R3.3)
        elif ch in _SENTENCE_END:
            j = i + 1
            while j < n and text[j] in _SENTENCE_END:
                j += 1
            while j < n and text[j] in ('"', "'", "」"):  # 닫는 인용부호는 문장에 포함
                j += 1
            sentences.append(text[start:j])
            start = j
            i = j
        else:
            i += 1
    if start < n:
        sentences.append(text[start:])
    return sentences


def _merge_sentences(sentences: list[str]) -> list[str]:
    """R3.4 — 누적 길이가 120자를 넘지 않는 범위에서 문장을 묶는다.
    R3.5 — 120자를 넘는 단일 문장은 그 자체로 단독 청크가 된다."""
    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        if current and len(current) + len(sentence) > MAX_CHUNK_CHARS_KO:
            chunks.append(current)
            current = sentence
        else:
            current += sentence
    if current:
        chunks.append(current)
    return chunks


def _content_segments(chapter_text: str) -> list[tuple[bool, int, str]]:
    """줄 단위로 훑어 (빈 줄 여부, 줄 수, 원문 텍스트) 구간으로 나눈다. 빈 줄 개수로
    R3.7의 `paragraph`/`scene`을 구분할 수 있는 게 이 구조 덕분이다 — analyze.py:37의
    `splitlines(keepends=True)`가 원문 줄바꿈을 보존해서 넘겨주기 때문이다."""
    segments: list[tuple[bool, int, str]] = []
    lines: list[str] = []
    blank: bool | None = None
    for line in chapter_text.splitlines(keepends=True):
        is_blank = line.strip() == ""
        if blank is None:
            blank = is_blank
        elif is_blank != blank:
            segments.append((blank, len(lines), "".join(lines)))
            lines = []
            blank = is_blank
        lines.append(line)
    if lines:
        segments.append((blank, len(lines), "".join(lines)))
    return segments


def _chunk_chapter(chapter_text: str) -> list[dict]:
    """한 챕터를 청크로 쪼갠다 (R3.1, R3.4~R3.6). 문단 경계에서 병합을 끊고(R3.6),
    빈 줄 텍스트는 버리지 않고 앞 청크에 붙여 문자를 하나도 잃지 않는다."""
    chunks: list[dict] = []
    prefix = ""  # 챕터 시작부의 빈 줄은 버리지 않고 첫 청크 앞에 붙인다
    for is_blank, line_count, text in _content_segments(chapter_text):
        if is_blank:
            if chunks:
                chunks[-1]["text"] += text  # 문단/장면 사이 빈 줄은 앞 청크에 붙인다
                chunks[-1]["boundary_after"] = "scene" if line_count >= 2 else "paragraph"
            else:
                prefix += text
            continue
        merged = _merge_sentences(_split_sentences(text))  # R3.6 — 이 문단 안에서만 병합
        merged[0] = prefix + merged[0]
        prefix = ""
        chunks.extend({"text": t, "boundary_after": "sentence"} for t in merged)
    if chunks:
        chunks[-1]["boundary_after"] = "chapter"  # R3.7(챕터 전환) · R3.8(전체 마지막 청크)
    elif prefix:
        # 챕터 전체가 빈 줄뿐이었다 — 내용 청크가 없어 prefix가 어디에도 못 붙는다.
        # 그래도 원문을 잃지 않으려면 그 자체를 청크로 남긴다.
        chunks.append({"text": prefix, "boundary_after": "chapter"})
    return chunks


def split_chunks(chapters: list[str]) -> list[list[dict]]:
    """`split_chapters()`의 출력을 받아 챕터별 청크 목록을 만든다 (R3.1~R3.8).
    챕터 그룹을 그대로 유지해 반환한다 — `id`·`chapter`·`order`는 T5의 몫이다."""
    return [_chunk_chapter(chapter) for chapter in chapters]
