"""입력 파일 디코딩. 챕터·청크 분할은 T3 이후에 붙인다."""

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
