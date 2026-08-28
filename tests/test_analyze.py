"""T2 — 인코딩 감지 테스트 (R1.1~R1.4)."""

import pytest

from nakdok.analyze import InputError, _split_sentences, read_book, split_chapters, split_chunks
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


def test_cli_exits_0_when_decoding_succeeds(tmp_path):
    """디코딩에 성공하면 analyze가 끝까지 진행해 exit 0으로 끝난다 (T5부터)."""
    assert main(["analyze", str(write_book(tmp_path, TEXT.encode("utf-8")))]) == 0


def test_missing_file_exits_2(tmp_path):
    """R1.5 — 존재하지 않는 파일은 exit 2."""
    assert main(["analyze", str(tmp_path / "없는파일.txt")]) == 2


def test_missing_file_reports_cause(tmp_path, capsys):
    """R1.5 — 실패 원인이 출력된다."""
    missing = tmp_path / "없는파일.txt"
    main(["analyze", str(missing)])

    # OSError 메시지는 경로를 repr로 넣어 백슬래시가 이중이 된다. 파일명으로 본다.
    err = capsys.readouterr().err
    assert missing.name in err
    assert "No such file" in err


def test_unreadable_path_exits_2(tmp_path, capsys):
    """R1.5 — 디렉토리처럼 읽을 수 없는 경로도 exit 2 + 원인 출력."""
    directory = tmp_path / "책디렉토리"
    directory.mkdir()

    assert main(["analyze", str(directory)]) == 2
    assert directory.name in capsys.readouterr().err


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
    assert main(["analyze", str(book)]) == 0
    assert "챕터 2개" in capsys.readouterr().out


# --- T4 청크 분할 (R3.1~R3.8) ---


def test_splits_at_sentence_boundary():
    """R3.1 — 누적 길이가 120자를 넘기면 문장 경계에서 정확히 갈라진다."""
    sentence_a = "가" * 80 + "."  # 81자
    sentence_b = "나" * 80 + "."  # 81자
    text = sentence_a + sentence_b + "\n"

    (chunks,) = split_chunks([text])

    assert len(chunks) == 2
    assert chunks[0]["text"] == sentence_a
    assert chunks[1]["text"] == sentence_b + "\n"
    assert chunks[0]["boundary_after"] == "sentence"


@pytest.mark.parametrize(
    "text",
    [
        '그가 "안녕하세요. 반갑습니다."라고 말했다.\n',
        "그가 '안녕하세요. 반갑습니다.'라고 말했다.\n",
        "그가 「안녕하세요. 반갑습니다.」라고 말했다.\n",
    ],
)
def test_quote_internal_period_is_not_a_boundary(text):
    """R3.2 — 따옴표(", ', 「」) 내부의 마침표는 문장 경계가 아니다.

    분할 계층(`_split_sentences`)을 직접 본다. 청크 개수만 보면 병합 단계가
    120자 이하 문장들을 도로 합쳐버려서, 내부 마침표에서 잘못 갈라져도
    청크 수가 똑같이 나와 버그가 가려진다.
    """
    assert len(_split_sentences(text)) == 2  # 실제 경계 1개(마지막 마침표) + 꼬리 개행

    (chunks,) = split_chunks([text])
    assert len(chunks) == 1
    assert chunks[0]["text"] == text


@pytest.mark.parametrize("text", ["몰라... 진짜야.\n", "몰라… 진짜야.\n"])
def test_ellipsis_is_not_a_boundary(text):
    """R3.3 — 줄임표(…, ...)는 문장 경계가 아니다. 분할 계층을 직접 본다(위 R3.2와 같은 이유)."""
    assert len(_split_sentences(text)) == 2  # 실제 경계 1개(마지막 마침표) + 꼬리 개행

    (chunks,) = split_chunks([text])
    assert len(chunks) == 1
    assert chunks[0]["text"] == text


def test_merges_sentences_under_120_chars():
    """R3.4 — 연속된 문장을 누적 120자 이하로 하나의 청크에 묶는다."""
    sentence = "다" * 29 + "."  # 30자 × 3 = 90자, 120 이하
    text = sentence * 3 + "\n"

    (chunks,) = split_chunks([text])

    assert len(chunks) == 1
    assert chunks[0]["text"] == text


def test_oversized_sentence_is_its_own_chunk():
    """R3.5 — 120자를 초과하는 단일 문장은 단독 청크가 된다."""
    long_sentence = "라" * 150 + "."  # 151자
    short_sentence = "마" + "."
    text = long_sentence + short_sentence + "\n"

    (chunks,) = split_chunks([text])

    assert len(chunks) == 2
    assert chunks[0]["text"] == long_sentence
    assert len(chunks[0]["text"]) > 120
    assert chunks[1]["text"] == short_sentence + "\n"


def test_chunk_does_not_merge_across_paragraph_boundary():
    """R3.6 — 청크가 문단 경계를 넘어 병합되지 않는다. 합쳐도 120자 이하지만 나뉜다."""
    text = "안녕.\n\n반가워.\n"

    (chunks,) = split_chunks([text])

    assert len(chunks) == 2
    assert chunks[0]["boundary_after"] == "paragraph"


def test_paragraph_boundary_at_exactly_one_blank_line():
    """R3.7 경계값 — 빈 줄 1개는 paragraph다."""
    text = "하나.\n\n둘.\n"

    (chunks,) = split_chunks([text])

    assert chunks[0]["boundary_after"] == "paragraph"


def test_scene_boundary_at_exactly_two_blank_lines():
    """R3.7 경계값 — 빈 줄 2개(그 이상)는 scene이다."""
    text = "하나.\n\n\n둘.\n"

    (chunks,) = split_chunks([text])

    assert chunks[0]["boundary_after"] == "scene"


def test_chapter_boundary_overrides_scene():
    """R3.7 우선순위 — 챕터 끝에 빈 줄 2개가 와도(scene 조건) 챕터 전환이 우선한다."""
    chapter1 = "안녕.\n\n\n"  # 뒤에 빈 줄만 있고 다음 문단이 없다 — scene처럼 보인다
    chapter2 = "반가워.\n"

    chunks1, chunks2 = split_chunks([chapter1, chapter2])

    assert chunks1[-1]["boundary_after"] == "chapter"  # scene이 아니다
    assert "".join(c["text"] for c in chunks1) == chapter1  # 빈 줄도 잃지 않는다


def test_last_chunk_of_entire_text_is_chapter():
    """R3.8 — 전체 텍스트의 마지막 청크는 chapter다."""
    chunks1, chunks2 = split_chunks(["첫 챕터.\n", "마지막 챕터.\n"])

    assert chunks2[-1]["boundary_after"] == "chapter"


@pytest.mark.parametrize("blank_chapter", ["\n\n", "   \n"])
def test_all_blank_chapter_preserves_characters(blank_chapter):
    """절대 규칙 1 — 챕터 전체가 빈 줄(또는 공백만 있는 줄)이어도 문자를 잃지 않는다.

    내용 청크가 하나도 없으면 그 챕터의 청크 목록에는 붙일 곳이 없다.
    그래도 원문 문자는 청크 하나로 남는다.
    """
    chapters = [blank_chapter, "제 1 장\n본문이다.\n"]

    result = split_chunks(chapters)

    assert "".join(c["text"] for chapter_chunks in result for c in chapter_chunks) == "".join(
        chapters
    )
    assert result[0] == [{"text": blank_chapter, "boundary_after": "chapter"}]


def test_chunk_split_preserves_every_character():
    """분할이 문자를 잃지 않는다 — CLAUDE.md 절대 규칙 1. 경계 4종을 함께 확인한다."""
    text = (
        "첫 문단이다. 계속된다.\n두 번째 줄도 첫 문단.\n"
        "\n"
        "둘째 문단.\n"
        "\n\n"
        "셋째 문단, 장면 전환 후.\n"
    )

    (chunks,) = split_chunks([text])

    assert len(chunks) == 3
    assert chunks[0]["boundary_after"] == "paragraph"
    assert chunks[1]["boundary_after"] == "scene"
    assert chunks[2]["boundary_after"] == "chapter"
    assert "".join(c["text"] for c in chunks) == text
