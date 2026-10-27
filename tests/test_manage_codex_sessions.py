from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

import build_manage_codex_sessions_gui as build_app
import manage_codex_sessions as app


REPO_ROOT = Path(__file__).resolve().parents[1]


def write_jsonl(path: Path, records: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False))
            handle.write("\n")


def create_session_fixture(
    codex_home: Path,
    *,
    session_id: str = "session-1",
    thread_name: str = "First session",
) -> Path:
    workspace_root = codex_home / "workspace-alpha"
    updated_at = "2026-10-12T10:00:00+00:00"
    rollout_path = codex_home / "sessions" / "workspace-alpha" / session_id / "rollout.jsonl"
    user_text = "How do I export this session?"
    assistant_text = "Use the new Markdown export flow."

    write_jsonl(
        codex_home / "session_index.jsonl",
        [{"id": session_id, "thread_name": thread_name, "updated_at": updated_at}],
    )
    write_jsonl(
        rollout_path,
        [
            {
                "type": "session_meta",
                "timestamp": updated_at,
                "ordinal": 0,
                "payload": {
                    "session_id": session_id,
                    "timestamp": updated_at,
                    "cwd": str(workspace_root),
                    "source": "codex-cli",
                    "cli_version": app.__version__,
                    "runtime_workspace_roots": [str(workspace_root)],
                },
            },
            {
                "timestamp": "2026-10-12T10:01:00+00:00",
                "ordinal": 1,
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "id": f"msg-user-{session_id}",
                    "role": "user",
                    "content": [{"type": "input_text", "text": user_text}],
                },
            },
            {
                "timestamp": "2026-10-12T10:02:00+00:00",
                "ordinal": 2,
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "id": f"msg-assistant-{session_id}",
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": assistant_text}],
                },
            },
        ],
    )
    return rollout_path


def test_build_session_summaries_collects_index_and_rollout_metadata(tmp_path: Path) -> None:
    codex_home = tmp_path / "codex-home"
    create_session_fixture(codex_home)

    summaries = app.build_session_summaries(codex_home)

    assert len(summaries) == 1
    summary = summaries[0]
    assert summary.session_id == "session-1"
    assert summary.thread_name == "First session"
    assert summary.file_count == 1
    assert summary.primary_source == "codex-cli"
    assert summary.primary_project == str(codex_home / "workspace-alpha")
    assert sorted(summary.cli_versions) == [app.__version__]


def test_move_to_trash_and_restore_round_trip(tmp_path: Path) -> None:
    codex_home = tmp_path / "codex-home"
    rollout_path = create_session_fixture(codex_home)
    session = app.build_session_summaries(codex_home)[0]

    delete_result = app.move_sessions_to_trash(codex_home, [session])

    assert delete_result.session_count == 1
    assert delete_result.deleted_file_count == 1
    assert delete_result.removed_index_entry_count == 1
    assert not rollout_path.exists()
    trashed_rollout_path = app.trash_sessions_dir(codex_home) / Path("workspace-alpha/session-1/rollout.jsonl")
    assert trashed_rollout_path.exists()
    assert app.read_index_entries(codex_home / "session_index.jsonl") == []

    trash_summaries = app.build_trash_summaries(codex_home)
    assert len(trash_summaries) == 1
    restore_result = app.restore_sessions_from_trash(codex_home, trash_summaries)

    assert restore_result.restored_session_count == 1
    assert restore_result.restored_file_count == 1
    assert restore_result.restored_index_entry_count == 1
    assert restore_result.skipped_session_ids == []
    assert rollout_path.exists()
    assert not trashed_rollout_path.exists()
    assert [entry.thread_name for entry in app.read_index_entries(codex_home / "session_index.jsonl")] == ["First session"]
    assert app.load_trash_records(codex_home) == []


def test_rename_session_updates_active_index_entries(tmp_path: Path) -> None:
    codex_home = tmp_path / "codex-home"
    create_session_fixture(codex_home)

    changed = app.rename_session(codex_home, "session-1", "Renamed active session")

    assert changed == 1
    assert [entry.thread_name for entry in app.read_index_entries(codex_home / "session_index.jsonl")] == ["Renamed active session"]


def test_rename_session_updates_trash_records(tmp_path: Path) -> None:
    codex_home = tmp_path / "codex-home"
    create_session_fixture(codex_home)
    session = app.build_session_summaries(codex_home)[0]
    app.move_sessions_to_trash(codex_home, [session])

    changed = app.rename_session(codex_home, "session-1", "Renamed trash session", in_trash=True)

    assert changed == 1
    trash_summaries = app.build_trash_summaries(codex_home)
    assert [summary.thread_name for summary in trash_summaries] == ["Renamed trash session"]

    app.restore_sessions_from_trash(codex_home, trash_summaries)
    assert [entry.thread_name for entry in app.read_index_entries(codex_home / "session_index.jsonl")] == ["Renamed trash session"]


def test_cli_query_json_outputs_expected_payload(tmp_path: Path) -> None:
    codex_home = tmp_path / "codex-home"
    create_session_fixture(codex_home)

    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "manage_codex_sessions.py"),
            "--lang",
            "en",
            "query",
            "--codex-home",
            str(codex_home),
            "--json",
            "--show-files",
        ],
        check=True,
        capture_output=True,
        cwd=REPO_ROOT,
        text=True,
    )

    payload = json.loads(result.stdout)

    assert len(payload) == 1
    assert payload[0]["id"] == "session-1"
    assert payload[0]["thread_name"] == "First session"
    assert payload[0]["rollout_paths"] == [str(codex_home / "sessions" / "workspace-alpha" / "session-1" / "rollout.jsonl")]


def test_build_session_markdown_includes_transcript(tmp_path: Path) -> None:
    codex_home = tmp_path / "codex-home"
    create_session_fixture(codex_home)

    session = app.build_session_summaries(codex_home)[0]
    markdown = app.build_session_markdown(session)

    assert markdown.startswith("# First session\n")
    assert "- Session ID: `session-1`" in markdown
    assert "## Transcript" in markdown
    assert "### User -" in markdown
    assert "How do I export this session?" in markdown
    assert "### Assistant -" in markdown
    assert "Use the new Markdown export flow." in markdown


def test_cli_export_markdown_writes_expected_file(tmp_path: Path) -> None:
    codex_home = tmp_path / "codex-home"
    create_session_fixture(codex_home)
    output_path = tmp_path / "exports" / "session-1.md"

    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "manage_codex_sessions.py"),
            "--lang",
            "en",
            "export",
            "--codex-home",
            str(codex_home),
            "--id",
            "session-1",
            "--output",
            str(output_path),
        ],
        check=True,
        capture_output=True,
        cwd=REPO_ROOT,
        text=True,
    )

    assert "Exported session session-1 to Markdown" in result.stdout
    assert output_path.exists()
    exported = output_path.read_text(encoding="utf-8")
    assert "# First session" in exported
    assert "How do I export this session?" in exported
    assert "Use the new Markdown export flow." in exported


def test_cli_and_gui_report_version() -> None:
    cli_result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "manage_codex_sessions.py"), "--version"],
        check=True,
        capture_output=True,
        cwd=REPO_ROOT,
        text=True,
    )
    gui_result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "manage_codex_sessions_gui.py"), "--version"],
        check=True,
        capture_output=True,
        cwd=REPO_ROOT,
        text=True,
    )

    assert app.__version__ in cli_result.stdout
    assert app.__version__ in gui_result.stdout


def test_gui_defaults_to_simplified_chinese_without_overrides(monkeypatch) -> None:
    monkeypatch.delenv("CODEX_UI_LANG", raising=False)
    monkeypatch.delenv("CODEX_LANG", raising=False)

    assert app.normalize_gui_language(None, system_locale_name="en_US") == "zh-CN"


def test_gui_language_override_env_is_still_respected(monkeypatch) -> None:
    monkeypatch.setenv("CODEX_UI_LANG", "en")
    monkeypatch.delenv("CODEX_LANG", raising=False)

    assert app.normalize_gui_language(None, system_locale_name="zh_CN") == "en"


def test_resolve_resume_working_directory_prefers_existing_workspace_root(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspace-alpha"
    workspace_root.mkdir()
    session = app.SessionSummary(session_id="session-1")
    session.workspace_roots_values.add(str(workspace_root))
    session.cwd_values.add(str(tmp_path / "missing"))

    assert app.resolve_resume_working_directory(session) == workspace_root


def test_build_codex_resume_terminal_command_windows_uses_new_console() -> None:
    command = app.build_codex_resume_terminal_command("session-1", platform_name="win32")

    assert command == ["cmd.exe", "/c", "start", "Codex Resume", "cmd.exe", "/k", "codex", "resume", "session-1"]


def test_launch_codex_resume_in_terminal_sets_codex_home_and_cwd(tmp_path: Path) -> None:
    codex_home = tmp_path / "codex-home"
    workspace_root = tmp_path / "workspace-alpha"
    workspace_root.mkdir()
    captured: dict[str, object] = {}

    def fake_which(name: str) -> str | None:
        if name == "codex":
            return "/usr/bin/codex"
        if name == "x-terminal-emulator":
            return "/usr/bin/x-terminal-emulator"
        return None

    def fake_popen(command: list[str], **kwargs: object) -> object:
        captured["command"] = command
        captured["kwargs"] = kwargs
        return object()

    app.launch_codex_resume_in_terminal(
        "session-1",
        codex_home=codex_home,
        working_directory=workspace_root,
        platform_name="linux",
        which_func=fake_which,
        popen_func=fake_popen,
    )

    assert captured["command"] == ["x-terminal-emulator", "-e", "bash", "-lc", "codex resume session-1; exec bash"]
    kwargs = captured["kwargs"]
    assert isinstance(kwargs, dict)
    assert kwargs["cwd"] == str(workspace_root)
    assert kwargs["env"]["CODEX_HOME"] == str(codex_home)


def test_launch_codex_resume_in_terminal_errors_when_codex_is_missing(tmp_path: Path) -> None:
    with pytest.raises(app.CodexExecutableNotFound):
        app.launch_codex_resume_in_terminal(
            "session-1",
            codex_home=tmp_path / "codex-home",
            platform_name="linux",
            which_func=lambda _name: None,
        )


def test_normalize_pyinstaller_args_preserves_unicode_empty_and_later_delimiters() -> None:
    # The first delimiter belongs to this wrapper; subsequent values are PyInstaller input.
    assert build_app.normalize_pyinstaller_args(["--", "--name", "Résumé 🧪", "--", ""]) == [
        "--name",
        "Résumé 🧪",
        "--",
        "",
    ]
    assert build_app.normalize_pyinstaller_args([]) == []


def test_build_pyinstaller_command_includes_icon_and_bundled_asset() -> None:
    command = build_app.build_pyinstaller_command(False, sys.executable, [])

    if sys.platform.startswith("win"):
        assert "--icon" in command
        assert str(build_app.ICON_PATH) in command
    else:
        assert "--icon" not in command
    add_data_index = command.index("--add-data")
    add_data_value = command[add_data_index + 1]
    expected_separator = ";" if sys.platform.startswith("win") else ":"
    assert add_data_value == f"{build_app.ICON_PATH}{expected_separator}assets"


def test_application_icon_asset_exists() -> None:
    assert app.resolve_runtime_asset_path(app.APP_ICON_RELATIVE_PATH).exists()


def test_normalize_string_list_preserves_unicode_and_json_falsy_values() -> None:
    """Metadata normalization must not discard values merely because they are falsy."""
    assert app.normalize_string_list([
        None,
        "",
        "工作目录",
        0,
        False,
        [],
        {"路径": "项目"},
    ]) == ["工作目录", "0", "false", "[]", '{"路径": "项目"}']
