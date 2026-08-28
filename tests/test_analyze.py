"""T2 — 인코딩 감지 테스트 (R1.1~R1.4)."""

import pytest

from nakdok.analyze import InputError, read_book, split_chapters
from nakdok.cli import main
from nakdok.config import DEFAULT_CHAPTER_PATTERNS

TEXT = "제 1 장\n\n한글 테스트 문장이다. 원문은 변형되지 않는다.\n"

# utf-8로는 디코딩되지 않고 cp949로만 읽히는 바이트열 (실측 확인)
CP949_BYTES = TEXT.encode("cp949")
# utf-8·cp949 둘 다 실패하는 바이트열 — 0xff는 cp949의 선행 바이트가 아니다
BROKEN_BYTES = b"\xff\xfe\xff"


def write_book(tmp_path, data: bytes):
    path = tmp_path / "book.txt"
    path.write_bytes(data)
    return path


def test_utf8_decodes_verbatim(tmp_path):
    """R1.1 — UTF-8 파일은 원문과 문자 단위로 동일하게 읽힌다."""
    assert read_book(write_book(tmp_path, TEXT.encode("utf-8"))) == TEXT


def test_cp949_fallback_reports_encoding(tmp_path, capsys):
    """R1.2 — CP949로 재시도해 성공하고, 감지된 인코딩을 표준 출력에 보고한다."""
    with pytest.raises(UnicodeDecodeError):
        CP949_BYTES.decode("utf-8")  # 픽스처가 UTF-8로는 안 읽히는지 확인

    assert read_book(write_book(tmp_path, CP949_BYTES)) == TEXT
    assert "cp949" in capsys.readouterr().out


def test_utf8_success_reports_nothing(tmp_path, capsys):
    """R1.2 — 폴백을 쓰지 않았으면 인코딩 보고도 없다."""
    read_book(write_book(tmp_path, TEXT.encode("utf-8")))
    assert capsys.readouterr().out == ""


def test_both_encodings_fail(tmp_path, capsys):
    """R1.3 — 둘 다 실패하면 exit 2 + 실패한 인코딩 목록."""
    assert main(["analyze", str(write_book(tmp_path, BROKEN_BYTES))]) == 2

    err = capsys.readouterr().err
    assert "utf-8" in err
    assert "cp949" in err


def test_decode_failure_raises(tmp_path):
    """R1.3 — 디코딩 함수 자체는 InputError를 낸다."""
    with pytest.raises(InputError):
        read_book(write_book(tmp_path, BROKEN_BYTES))


def test_empty_file_exits_2(tmp_path):
    """R1.4 — 0바이트(=0자) 파일은 exit 2."""
    assert main(["analyze", str(write_book(tmp_path, b""))]) == 2


def test_empty_means_zero_characters(tmp_path):
    """R1.4 — 0자 판정은 공백이 아니라 길이 0 기준이다."""
    with pytest.raises(InputError):
        read_book(write_book(tmp_path, b""))
    assert read_book(write_book(tmp_path, " \n".encode("utf-8"))) == " \n"


def test_cli_exits_1_when_decoding_succeeds(tmp_path):
    """디코딩에 성공하면 아직 미구현이므로 exit 1로 끝난다."""
    assert main(["analyze", str(write_book(tmp_path, TEXT.encode("utf-8")))]) == 1


# --- T3 챕터 분할 (R2.1~R2.5) ---


@pytest.mark.parametrize(
    "heading", ["제 1 장", "제1화", "제 3 부", "3.", "12", "Chapter 4", "chapter 12"]
)
def test_default_patterns_match(heading):
    """R2.2 — 기본 정규식 3종이 각각 매칭된다."""
    chapters = split_chapters(f"앞머리\n{heading}\n본문\n", DEFAULT_CHAPTER_PATTERNS)
    assert len(chapters) == 2


def test_plain_line_is_not_a_boundary():
    """경계가 아닌 줄에서는 나뉘지 않는다 — 위 테스트의 대조군."""
    chapters = split_chapters("앞머리\n그냥 문장이다.\n본문\n", DEFAULT_CHAPTER_PATTERNS)
    assert len(chapters) == 1


def test_boundary_line_starts_its_chapter():
    """경계 줄 자체는 그 챕터의 첫 줄로 들어간다."""
    chapters = split_chapters("서문\n제 1 장\n본문\n", DEFAULT_CHAPTER_PATTERNS)
    assert chapters[1].startswith("제 1 장")


def test_no_boundary_makes_one_chapter_and_warns(capsys):
    """R2.4 — 경계가 없으면 단일 챕터 + 경고."""
    text = "경계가 없는 글이다.\n두 번째 줄이다.\n"
    assert split_chapters(text, DEFAULT_CHAPTER_PATTERNS) == [text]
    assert "경고" in capsys.readouterr().out


def test_no_warning_when_boundary_found(capsys):
    """R2.4 — 경계가 있으면 경고하지 않는다."""
    split_chapters("제 1 장\n본문\n", DEFAULT_CHAPTER_PATTERNS)
    assert "경고" not in capsys.readouterr().out


def test_reports_chapter_count_and_sizes(capsys):
    """R2.5 — 챕터 수와 각 챕터 문자 수를 표준 출력에 보고한다."""
    chapters = split_chapters("제 1 장\n가나다\n제 2 장\n라마\n", DEFAULT_CHAPTER_PATTERNS)

    out = capsys.readouterr().out
    assert "챕터 2개" in out
    for chapter in chapters:
        assert f"{len(chapter)}자" in out


def test_split_preserves_every_character():
    """분할이 문자를 잃지 않는다 — CLAUDE.md 절대 규칙 1."""
    text = "서문이다.\n\n제 1 장\n본문 하나.\n\n2.\n본문 둘.\nChapter 3\n끝."
    chapters = split_chapters(text, DEFAULT_CHAPTER_PATTERNS)

    assert len(chapters) == 4
    assert chapters[0] == "서문이다.\n\n"  # 첫 경계 앞 텍스트가 버려지지 않는다
    assert "".join(chapters) == text


def test_config_pattern_is_used_by_split(tmp_path, capsys):
    """R2.3 — config의 정규식이 실제 분할에 쓰인다 (CLI 경로)."""
    nakdok_dir = tmp_path / ".nakdok"
    nakdok_dir.mkdir()
    (nakdok_dir / "config.yaml").write_text("chapter_pattern: '^### '\n", encoding="utf-8")

    # 기본 정규식이라면 "제 1 장"에서 나뉘지만, config 정규식은 "### "에서만 나뉜다
    book = write_book(tmp_path, "제 1 장\n본문\n### 진짜 경계\n뒷부분\n".encode("utf-8"))
    assert main(["analyze", str(book)]) == 1
    assert "챕터 2개" in capsys.readouterr().out
