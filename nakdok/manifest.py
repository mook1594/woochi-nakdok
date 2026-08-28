"""매니페스트 스키마·text_hash·읽기/쓰기 (T5, R4.1~R4.5, R10.1)."""

import hashlib
import json
from pathlib import Path

# R4.2 — 청크마다 정확히 이 10개 필드만 갖는다.
FIELDS = (
    "id",
    "chapter",
    "order",
    "boundary_after",
    "text",
    "text_hash",
    "voice",
    "speed",
    "audio_path",
    "duration_ms",
)

# 해시 입력을 이 문자로 구분한다. 책 본문에 나타날 수 없는 제어문자라, 구분자
# 없이 이어붙일 때 생기는 충돌(text="가나"+voice="M3" == text="가나M"+voice="3")을 막는다.
_HASH_SEP = "\x00"


def manifest_path(book_path: str | Path) -> Path:
    """`.nakdok/manifest.json`은 책 파일 옆에 생긴다. config.py의 `config_path()`와 같은 규칙."""
    return Path(book_path).parent / ".nakdok" / "manifest.json"


def text_hash(text: str, voice: str, speed: float) -> str:
    """R10.1 — SHA256(치환 후 텍스트 + voice + speed).

    Phase 1은 치환 사전(lexicon, R8)이 없으므로 치환 후 텍스트는 곧 원문이다.
    """
    payload = _HASH_SEP.join([text, voice, str(speed)])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_manifest(
    chapters_chunks: list[list[dict]],
    voice: str,
    speed: float,
    existing: list[dict] | None = None,
) -> list[dict]:
    """`split_chunks()`의 챕터별 청크 목록에 id/chapter/order를 부여하고 나머지 필드를 채운다.

    R4.4 — `existing`(이전 매니페스트)에서 `text_hash`가 같은 항목의 `audio_path`·
    `duration_ms`를 그대로 옮긴다. 텍스트·voice·speed 중 하나라도 바뀌면 해시가
    달라져 캐시를 못 찾으므로 자연히 빈 값으로 리셋된다.
    """
    cache = {item["text_hash"]: item for item in (existing or [])}
    manifest = []
    for chapter_idx, chunks in enumerate(chapters_chunks, start=1):
        for order, chunk in enumerate(chunks, start=1):
            text = chunk["text"]
            h = text_hash(text, voice, speed)
            prev = cache.get(h)
            manifest.append(
                {
                    # id 형식은 요구사항에 없다. "챕터-순번"을 쓴다 — R5.5가 실패 로그에
                    # 이 id를 그대로 출력하므로, 사람이 몇 번째 챕터의 몇 번째 청크인지
                    # 바로 알아볼 수 있어야 한다.
                    "id": f"{chapter_idx}-{order}",
                    "chapter": chapter_idx,
                    "order": order,
                    "boundary_after": chunk["boundary_after"],
                    "text": text,
                    "text_hash": h,
                    "voice": voice,
                    "speed": speed,
                    "audio_path": prev["audio_path"] if prev else "",
                    "duration_ms": prev["duration_ms"] if prev else None,
                }
            )
    return manifest


def load_manifest(book_path: str | Path) -> list[dict]:
    """매니페스트가 없으면 빈 목록 — 첫 `analyze` 실행은 기존 항목이 없는 것과 같다."""
    path = manifest_path(book_path)
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def save_manifest(book_path: str | Path, manifest: list[dict]) -> None:
    path = manifest_path(book_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # ensure_ascii=False — 안 하면 한글이 \uXXXX로 박혀 사람이 매니페스트를 못 읽는다.
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
