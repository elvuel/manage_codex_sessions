import argparse

from manage_codex_sessions import (
    CLI_TRANSLATIONS,
    __version__,
    configure_stdout,
    detect_requested_language,
    format_localized_text,
    launch_gui,
    normalize_language,
    resolve_codex_home,
)


def build_parser(language: str | None = None) -> argparse.ArgumentParser:
    build_language = normalize_language(language or detect_requested_language(), environment_keys=("CODEX_LANG",))

    def localize(key: str, **kwargs: object) -> str:
        return format_localized_text(CLI_TRANSLATIONS, build_language, key, **kwargs)

    parser = argparse.ArgumentParser(description=localize("standalone_gui_description"))
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--codex-home", help=localize("codex_home_help"))
    parser.add_argument("--lang", metavar="LANG", help=localize("gui_lang_help"))
    return parser


def main() -> int:
    configure_stdout()
    args = build_parser().parse_args()
    return launch_gui(resolve_codex_home(args.codex_home), language=args.lang)


if __name__ == "__main__":
    raise SystemExit(main())

