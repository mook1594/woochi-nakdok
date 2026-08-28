"""T5 — 매니페스트 생성 테스트 (R4.1~R4.5, R10.1)."""

from nakdok.analyze import split_chapters, split_chunks
from nakdok.cli import main
from nakdok.manifest import FIELDS, build_manifest, load_manifest, manifest_path, save_manifest, text_hash

TEXT = "제 1 장\n첫 문장이다. 둘째 문장이다.\n\n다음 문단.\n"


def chunks_for(text: str) -> list[list[dict]]:
    return split_chunks(split_chapters(text, (r"제\s*\d+\s*[장화부]",)))


def test_analyze_creates_manifest_file(tmp_path):
    """R4.1 — analyze 명령이 완료되면 `.nakdok/manifest.json`이 생긴다."""
    book = tmp_path / "book.txt"
    book.write_text(TEXT, encoding="utf-8")

    assert main(["analyze", str(book)]) == 0
    assert manifest_path(book).exists()


def test_chunk_has_exactly_ten_fields():
    """R4.2 — 필드 집합이 정확히 10개다. 부분집합이 아니라 `==`로 비교한다."""
    manifest = build_manifest(chunks_for(TEXT), "M3", 0.95)

    assert manifest  # 픽스처가 청크를 만들지 않으면 아래 비교가 공허하게 통과한다
    for chunk in manifest:
        assert set(chunk.keys()) == set(FIELDS)


def test_text_field_is_verbatim():
    """R4.3 — `text` 필드를 이어붙이면 원문과 문자 단위로 동일하다."""
    manifest = build_manifest(chunks_for(TEXT), "M3", 0.95)

    assert "".join(chunk["text"] for chunk in manifest) == TEXT


def test_rerun_preserves_audio_path_and_duration_for_same_hash():
    """R4.4 — 재실행 시 text_hash가 같은 항목의 audio_path/duration_ms를 보존한다."""
    first = build_manifest(chunks_for(TEXT), "M3", 0.95)
    for chunk in first:
        chunk["audio_path"] = f".nakdok/audio/{chunk['text_hash']}.wav"
        chunk["duration_ms"] = 1234

    second = build_manifest(chunks_for(TEXT), "M3", 0.95, existing=first)

    assert [c["audio_path"] for c in second] == [c["audio_path"] for c in first]
    assert [c["duration_ms"] for c in second] == [c["duration_ms"] for c in first]


def test_rerun_resets_when_text_changes():
    """R4.4 대조군 — 캐시는 위치가 아니라 text_hash로 찾는다. 텍스트가 바뀌면 초기화된다."""
    first = build_manifest(chunks_for(TEXT), "M3", 0.95)
    for chunk in first:
        chunk["audio_path"] = f".nakdok/audio/{chunk['text_hash']}.wav"
        chunk["duration_ms"] = 1234

    changed_text = TEXT.replace("첫 문장이다.", "바뀐 문장이다.")
    second = build_manifest(chunks_for(changed_text), "M3", 0.95, existing=first)

    changed = [c for c in second if "바뀐" in c["text"]]
    assert changed
    assert all(c["audio_path"] == "" and c["duration_ms"] is None for c in changed)


def test_voice_and_speed_are_assigned_to_every_chunk():
    """R4.5 — build_manifest에 넘긴 voice/speed가 모든 청크에 배정된다."""
    manifest = build_manifest(chunks_for(TEXT), "F2", 1.1)

    assert all(chunk["voice"] == "F2" for chunk in manifest)
    assert all(chunk["speed"] == 1.1 for chunk in manifest)


def test_hash_is_deterministic():
    """R10.1 — 같은 입력은 항상 같은 해시를 낸다."""
    assert text_hash("가나다", "M3", 0.95) == text_hash("가나다", "M3", 0.95)


def test_hash_changes_when_voice_changes():
    """R10.1 — voice가 바뀌면 해시도 바뀐다."""
    assert text_hash("가나다", "M3", 0.95) != text_hash("가나다", "F2", 0.95)


def test_hash_changes_when_speed_changes():
    """R10.1 — speed가 바뀌면 해시도 바뀐다."""
    assert text_hash("가나다", "M3", 0.95) != text_hash("가나다", "M3", 1.05)


def test_hash_avoids_concatenation_collision():
    """구분자 없이 이어붙이면 text="가나"+voice="M3" 와 text="가나M"+voice="3" 이 같은 문자열이 된다.
    구분자가 이 충돌을 막는지 직접 확인한다."""
    assert text_hash("가나", "M3", 0.95) != text_hash("가나M", "3", 0.95)


def test_id_format_is_chapter_dash_order():
    """id 형식(요구사항 미지정) — "챕터-순번"(둘 다 1부터). 실패 로그(R5.5)에서 위치를 바로
    알아볼 수 있다. 기댓값은 manifest에서 뽑지 않고 리터럴로 적는다 — 그래야 chapter/order의
    시작값이 실제로 고정된다."""
    # 챕터 1은 문단 경계(빈 줄)로 청크가 둘로 갈라지고, 챕터 2는 청크 하나다.
    chapters_chunks = chunks_for("제 1 장\n하나.\n\n둘.\n제 2 장\n셋.\n")
    manifest = build_manifest(chapters_chunks, "M3", 0.95)

    assert [(c["chapter"], c["order"], c["id"]) for c in manifest] == [
        (1, 1, "1-1"),
        (1, 2, "1-2"),
        (2, 1, "2-1"),
    ]


def test_manifest_path_is_beside_book_not_cwd(tmp_path, monkeypatch):
    """config.py의 config_path()와 같은 규칙 — 매니페스트는 책 옆 `.nakdok/`에 쓴다."""
    book_dir = tmp_path / "책"
    book_dir.mkdir()
    book = book_dir / "book.txt"

    cwd = tmp_path / "다른곳"
    cwd.mkdir()
    monkeypatch.chdir(cwd)

    assert manifest_path(book) == book_dir / ".nakdok" / "manifest.json"


def test_save_and_load_manifest_roundtrip(tmp_path):
    """저장 후 읽으면 같은 내용이 나오고, 한글이 \\uXXXX로 깨지지 않는다."""
    book = tmp_path / "book.txt"
    manifest = build_manifest(chunks_for(TEXT), "M3", 0.95)

    save_manifest(book, manifest)
    raw = manifest_path(book).read_text(encoding="utf-8")

    assert "\\u" not in raw  # ensure_ascii=False
    assert load_manifest(book) == manifest


def test_load_manifest_returns_empty_list_when_missing(tmp_path):
    """매니페스트가 아직 없으면 빈 목록 — 첫 analyze는 기존 항목이 없는 것과 같다."""
    assert load_manifest(tmp_path / "book.txt") == []
