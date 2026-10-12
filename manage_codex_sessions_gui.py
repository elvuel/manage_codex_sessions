from manage_codex_sessions import configure_stdout, launch_gui, resolve_codex_home


if __name__ == "__main__":
    configure_stdout()
    raise SystemExit(launch_gui(resolve_codex_home(None)))

