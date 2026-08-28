"""T1 — CLI 파서와 진입점 테스트."""

import argparse

import pytest

from nakdok.cli import build_parser, main


def subcommand_names(parser: argparse.ArgumentParser) -> set[str]:
    """파서에 등록된 서브커맨드 이름 집합."""
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return set(action.choices)
    raise AssertionError("서브파서가 등록되지 않았다")


def test_subcommands_are_exactly_four():
    """analyze/synth/build/run 4개만 등록한다."""
    assert subcommand_names(build_parser()) == {"analyze", "synth", "build", "run"}


def test_analyze_requires_book():
    """analyze를 인자 없이 호출하면 0이 아닌 코드로 끝난다."""
    with pytest.raises(SystemExit) as exc:
        build_parser().parse_args(["analyze"])
    assert exc.value.code != 0


def test_run_requires_book():
    """run을 인자 없이 호출하면 0이 아닌 코드로 끝난다."""
    with pytest.raises(SystemExit) as exc:
        build_parser().parse_args(["run"])
    assert exc.value.code != 0


def test_synth_and_build_take_no_args():
    """synth와 build는 인자 없이도 파싱에 성공한다."""
    parser = build_parser()
    assert parser.parse_args(["synth"]).command == "synth"
    assert parser.parse_args(["build"]).command == "build"


@pytest.mark.parametrize(
    "argv",
    [["analyze", "book.txt"], ["synth"], ["build"], ["run", "book.txt"]],
)
def test_every_command_exits_nonzero(argv):
    """아직 구현되지 않았으므로 모든 명령이 0이 아닌 코드를 반환한다."""
    assert main(argv) != 0
