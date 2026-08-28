"""서브커맨드 파서와 진입점. 각 명령의 실제 로직은 T2 이후에 붙인다."""

import argparse
import sys

from nakdok.analyze import InputError, read_book, split_chapters, split_chunks
from nakdok.config import chapter_patterns, voice_and_speed
from nakdok.manifest import build_manifest, load_manifest, save_manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="nakdok",
        description="한국어 txt 전자책을 낭독해 m4b 오디오북으로 만든다",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    analyze = sub.add_parser("analyze", help="챕터/청크 분할 → .nakdok/manifest.json")
    analyze.add_argument("book", help="입력 txt 파일")

    sub.add_parser("synth", help="manifest 기준, 해시가 바뀐 청크만 합성")
    sub.add_parser("build", help="ffmpeg concat → <book>.m4b")

    run = sub.add_parser("run", help="analyze → synth → build")
    run.add_argument("book", help="입력 txt 파일")

    return parser


def main(argv: list[str] | None = None) -> int:
    # 출력이 파이프로 넘어가면 인코딩이 cp1252로 잡혀 한글에서 크래시한다.
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    args = build_parser().parse_args(argv)
    if args.command == "analyze":
        try:
            text = read_book(args.book)
        except (InputError, OSError) as e:
            print(e, file=sys.stderr)
            return 2
        chapters = split_chapters(text, chapter_patterns(args.book))
        chunks = split_chunks(chapters)
        voice, speed = voice_and_speed(args.book)
        manifest = build_manifest(chunks, voice, speed, existing=load_manifest(args.book))
        save_manifest(args.book, manifest)  # R4.1
        return 0
    print(f"nakdok {args.command}: 아직 구현되지 않았다", file=sys.stderr)
    return 1
