"""`.nakdok/config.yaml` 로딩. 읽는 키: `chapter_pattern`, `voice`, `speed`."""

from pathlib import Path

import yaml

DEFAULT_CHAPTER_PATTERNS = (
    r"제\s*\d+\s*[장화부]",
    r"^\d+\.?\s*$",
    r"^[Cc]hapter\s+\d+",
)

# R4.5 — voice/speed가 config에 없을 때 쓰는 기본값. architecture.md D7의 자리표시자이고
# Phase 0 청취 결과로 확정한다.
DEFAULT_VOICE = "M3"
DEFAULT_SPEED = 0.95


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


def voice_and_speed(book_path: str | Path) -> tuple[str, float]:
    """R4.5 — `voice`/`speed`가 config에 없으면 기본값 `M3`/`0.95`를 쓴다."""
    path = config_path(book_path)
    if not path.exists():
        return DEFAULT_VOICE, DEFAULT_SPEED
    config = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return config.get("voice", DEFAULT_VOICE), config.get("speed", DEFAULT_SPEED)
