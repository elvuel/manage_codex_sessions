import argparse

from manage_codex_sessions import configure_stdout, launch_gui, resolve_codex_home


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Launch the manage_codex_sessions Qt GUI.")
    parser.add_argument("--codex-home", help="Codex data directory. Defaults to CODEX_HOME or ~/.codex.")
    parser.add_argument("--lang", help="GUI language: system, en, zh-CN. Defaults to system or CODEX_UI_LANG.")
    return parser


if __name__ == "__main__":
    configure_stdout()
    args = build_parser().parse_args()
    raise SystemExit(launch_gui(resolve_codex_home(args.codex_home), language=args.lang))

