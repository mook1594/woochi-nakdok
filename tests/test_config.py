"""T3 — 설정 로딩 테스트 (R2.3)."""

from nakdok.config import DEFAULT_CHAPTER_PATTERNS, chapter_patterns


def write_config(book_path, body: str):
    """책 파일 옆 `.nakdok/config.yaml`을 만든다."""
    nakdok_dir = book_path.parent / ".nakdok"
    nakdok_dir.mkdir(parents=True, exist_ok=True)
    (nakdok_dir / "config.yaml").write_text(body, encoding="utf-8")


def test_defaults_when_no_config(tmp_path):
    """config.yaml이 없으면 기본 정규식 3종을 쓴다."""
    assert chapter_patterns(tmp_path / "book.txt") == DEFAULT_CHAPTER_PATTERNS
    assert len(DEFAULT_CHAPTER_PATTERNS) == 3


def test_config_pattern_replaces_defaults(tmp_path):
    """R2.3 — chapter_pattern이 있으면 기본값을 대체한다 (추가가 아니다)."""
    book = tmp_path / "book.txt"
    write_config(book, "chapter_pattern: '^### '\n")

    assert chapter_patterns(book) == ("^### ",)


def test_empty_config_falls_back(tmp_path):
    """빈 config.yaml은 오류가 아니라 기본값이다."""
    book = tmp_path / "book.txt"
    write_config(book, "")

    assert chapter_patterns(book) == DEFAULT_CHAPTER_PATTERNS


def test_config_read_next_to_book_not_cwd(tmp_path, monkeypatch):
    """설정은 책 파일 옆 `.nakdok/`에서 읽는다. 현재 작업 디렉토리가 아니다."""
    book_dir = tmp_path / "책"
    book_dir.mkdir()
    book = book_dir / "book.txt"
    write_config(book, "chapter_pattern: '^책옆'\n")

    # cwd에는 다른 설정을 놓고, 그쪽이 읽히지 않는 것을 확인한다
    cwd = tmp_path / "다른곳"
    cwd.mkdir()
    write_config(cwd / "dummy.txt", "chapter_pattern: '^현재디렉토리'\n")
    monkeypatch.chdir(cwd)

    assert chapter_patterns(book) == ("^책옆",)


def test_config_beside_cwd_is_ignored(tmp_path, monkeypatch):
    """책 옆에 설정이 없으면, cwd에 설정이 있어도 기본값을 쓴다."""
    book_dir = tmp_path / "책"
    book_dir.mkdir()

    cwd = tmp_path / "다른곳"
    cwd.mkdir()
    write_config(cwd / "dummy.txt", "chapter_pattern: '^현재디렉토리'\n")
    monkeypatch.chdir(cwd)

    assert chapter_patterns(book_dir / "book.txt") == DEFAULT_CHAPTER_PATTERNS
