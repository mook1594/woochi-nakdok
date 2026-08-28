"""입력 파일 디코딩과 챕터 분할. 청크 분할은 T4 이후에 붙인다."""

import re
from pathlib import Path

# 시도 순서. R1.3의 "실패한 인코딩 목록"도 이 순서를 그대로 쓴다.
ENCODINGS = ("utf-8", "cp949")


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
