"""`.nakdok/config.yaml` 로딩. 지금 읽는 키는 `chapter_pattern` 하나뿐이다."""

from pathlib import Path

import yaml

DEFAULT_CHAPTER_PATTERNS = (
    r"제\s*\d+\s*[장화부]",
    r"^\d+\.?\s*$",
    r"^[Cc]hapter\s+\d+",
)


def config_path(book_path: str | Path) -> Path:
    """`.nakdok/`는 책 파일 옆에 생긴다. 현재 작업 디렉토리 기준이 아니다."""
    return Path(book_path).parent / ".nakdok" / "config.yaml"


def chapter_patterns(book_path: str | Path) -> tuple[str, ...]:
    """R2.3 — `chapter_pattern`이 있으면 기본 정규식 3종을 대체한다."""
    path = config_path(book_path)
    if not path.exists():
        return DEFAULT_CHAPTER_PATTERNS
    config = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    pattern = config.get("chapter_pattern")
    return (pattern,) if pattern else DEFAULT_CHAPTER_PATTERNS
