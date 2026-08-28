"""T2 — 인코딩 감지 테스트 (R1.1~R1.4)."""

import pytest

from nakdok.analyze import InputError, read_book
from nakdok.cli import main

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
