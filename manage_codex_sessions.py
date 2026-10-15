from __future__ import annotations

import argparse
import json
import locale
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


__version__ = "1.1.1"
APP_ICON_RELATIVE_PATH = Path("assets") / "manage_codex_sessions.ico"


def configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")


def parse_iso8601(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def isoformat_or_none(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def stringify_metadata(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def normalize_string_list(values: Iterable[object]) -> list[str]:
    normalized: list[str] = []
    for value in values:
        rendered = stringify_metadata(value)
        if rendered:
            normalized.append(rendered)
    return normalized


def format_timestamp(value: datetime | None) -> str:
    if value is None:
        return "-"
    return value.astimezone().strftime("%Y-%m-%d %H:%M:%S %z")


def format_bytes(size: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    value = float(size)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{int(value)}{unit}" if unit == "B" else f"{value:.1f}{unit}"
        value /= 1024
    return f"{size}B"


def truncate(text: str, width: int) -> str:
    if len(text) <= width:
        return text
    if width <= 1:
        return text[:width]
    return text[: width - 1] + "…"


def ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def default_codex_home() -> Path:
    configured = os.environ.get("CODEX_HOME")
    return Path(configured).expanduser() if configured else Path.home() / ".codex"


def resolve_codex_home(codex_home: str | None) -> Path:
    return Path(codex_home).expanduser() if codex_home else default_codex_home()


def resolve_runtime_asset_path(relative_path: str | Path) -> Path:
    candidate = Path(relative_path)
    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root is not None:
        bundled = Path(str(bundle_root)) / candidate
        if bundled.exists():
            return bundled
    return Path(__file__).resolve().parent / candidate


GUI_TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": {
        "window_title": "Codex Session Manager",
        "filter_project_label": "Project",
        "filter_search_label": "Search",
        "all_projects": "All Projects",
        "filter_placeholder": "Filter by project, session id, title, cwd, or source",
        "unknown_project": "(Unknown Project)",
        "header_project": "Project",
        "header_updated": "Updated",
        "header_deleted": "Deleted",
        "header_files": "Files",
        "header_size": "Size",
        "header_source": "Source",
        "header_session_id": "Session ID",
        "header_thread": "Thread",
        "header_cwd": "CWD",
        "browse": "Browse",
        "refresh": "Refresh",
        "language_label": "Language",
        "language_option_zh_cn": "简体中文",
        "language_option_en": "English",
        "qt_backend": "Qt: {binding_name}",
        "active_title": "Active Sessions",
        "trash_title": "Trash",
        "select_all": "Select All",
        "clear_selection": "Clear Selection",
        "export_markdown": "Export Markdown",
        "rename": "Rename",
        "delete_to_trash": "Move to Trash",
        "restore_selected": "Restore Selected",
        "purge_selected": "Delete Selected Permanently",
        "purge_all": "Empty Trash",
        "ready": "Ready",
        "choose_codex_home": "Choose CODEX_HOME",
        "load_failed_title": "Load Failed",
        "copy_session_id_action": "Copy Session ID",
        "copy_session_id_body": "Session ID copied.",
        "copy_session_ids_body": "Copied {count} session IDs.",
        "export_markdown_title": "Export Session Markdown",
        "export_markdown_filter": "Markdown Files (*.md);;All Files (*)",
        "export_single_select_title": "Select One Session",
        "export_single_select_body": "Markdown export supports exactly one selected session.",
        "export_complete_title": "Export Complete",
        "export_complete_body": "Exported Markdown to:\n{output_path}",
        "export_failed_title": "Export Failed",
        "status_summary": "CODEX_HOME: {codex_home} | Active {active_count} | Trash {trash_count} | Current: {title} Visible {visible_count} | Selected {selected_count}",
        "rename_session_title": "Rename Session",
        "rename_session_label": "New name:",
        "rename_failed_title": "Rename Failed",
        "rename_missing_session": "Session not found: {session_id}",
        "rename_single_select_title": "Select One Session",
        "rename_single_select_body": "Rename supports exactly one selected session.",
        "no_selection_title": "No Selection",
        "select_active_first": "Select one or more active sessions first.",
        "select_trash_first": "Select one or more trashed sessions first.",
        "confirm_delete_title": "Confirm Delete",
        "confirm_delete_body": "Move the following sessions to trash:\n\n{preview}",
        "more_sessions": "... {count} more sessions",
        "delete_complete_title": "Delete Complete",
        "delete_action_moved": "Moved to trash",
        "delete_action_permanent": "Permanently deleted",
        "delete_action_move_verb": "move to trash",
        "delete_action_permanent_verb": "permanently delete",
        "restore_action": "restore",
        "purge_from_trash_action": "permanently delete from trash",
        "delete_summary": "{action} {session_count} session(s), {deleted_file_count} rollout file(s), and {removed_index_entry_count} index record(s).",
        "confirm_restore_title": "Confirm Restore",
        "confirm_restore_body": "Restore the selected {count} session(s)?",
        "restore_complete_title": "Restore Complete",
        "restore_summary": "Restored {restored_session_count} session(s), {restored_file_count} rollout file(s), and {restored_index_entry_count} index record(s).",
        "restore_summary_skipped": " Skipped {count} conflicted session(s): {ids}",
        "confirm_purge_selected_title": "Confirm Permanent Delete",
        "confirm_purge_selected_body": "Permanently delete the selected {count} trashed session(s)? This action cannot be undone.",
        "purge_complete_title": "Delete Complete",
        "purge_summary": "Permanently deleted {session_count} trashed session(s) and {deleted_file_count} rollout file(s).",
        "trash_empty_title": "Trash Is Empty",
        "trash_empty_body": "There are no trashed sessions to clear.",
        "confirm_purge_all_title": "Empty Trash",
        "confirm_purge_all_body": "Permanently delete all {count} session(s) in trash? This action cannot be undone.",
        "empty_trash_complete_title": "Trash Emptied",
        "already_running_title": "Already Running",
        "already_running_body": "`manage_codex_sessions` GUI is already running. Only one instance is allowed.",
    },
    "zh-CN": {
        "window_title": "Codex Session 管理器",
        "filter_project_label": "项目",
        "filter_search_label": "搜索",
        "all_projects": "全部项目",
        "filter_placeholder": "按项目、session id、标题、cwd、source 过滤",
        "unknown_project": "(未知项目)",
        "header_project": "项目",
        "header_updated": "更新时间",
        "header_deleted": "删除时间",
        "header_files": "文件数",
        "header_size": "大小",
        "header_source": "来源",
        "header_session_id": "Session ID",
        "header_thread": "Thread",
        "header_cwd": "CWD",
        "browse": "浏览",
        "refresh": "刷新",
        "language_label": "界面语言",
        "language_option_zh_cn": "简体中文",
        "language_option_en": "English",
        "qt_backend": "Qt: {binding_name}",
        "active_title": "活动 sessions",
        "trash_title": "回收站",
        "select_all": "全选",
        "clear_selection": "清空选择",
        "export_markdown": "导出 Markdown",
        "rename": "重命名",
        "delete_to_trash": "删除到回收站",
        "restore_selected": "恢复所选",
        "purge_selected": "彻底删除所选",
        "purge_all": "清空回收站",
        "ready": "就绪",
        "choose_codex_home": "选择 CODEX_HOME",
        "load_failed_title": "加载失败",
        "copy_session_id_action": "复制 Session ID",
        "copy_session_id_body": "session_id已复制",
        "copy_session_ids_body": "已复制 {count} 个 session_id",
        "export_markdown_title": "导出 Session Markdown",
        "export_markdown_filter": "Markdown 文件 (*.md);;所有文件 (*)",
        "export_single_select_title": "请选择一条",
        "export_single_select_body": "导出 Markdown 仅支持单选 session。",
        "export_complete_title": "导出完成",
        "export_complete_body": "Markdown 已导出到：\n{output_path}",
        "export_failed_title": "导出失败",
        "status_summary": "CODEX_HOME: {codex_home} | 活动 {active_count} | 回收站 {trash_count} | 当前: {title} 显示 {visible_count} | 已选 {selected_count}",
        "rename_session_title": "重命名 session",
        "rename_session_label": "新的名称：",
        "rename_failed_title": "重命名失败",
        "rename_missing_session": "未找到 session: {session_id}",
        "rename_single_select_title": "请选择一条",
        "rename_single_select_body": "重命名只支持单选 session。",
        "no_selection_title": "未选择",
        "select_active_first": "请先选择一个或多个活动 session。",
        "select_trash_first": "请先选择一个或多个回收站 session。",
        "confirm_delete_title": "确认删除",
        "confirm_delete_body": "将以下 session 移入回收站：\n\n{preview}",
        "more_sessions": "... 其余 {count} 个 session",
        "delete_complete_title": "删除完成",
        "delete_action_moved": "移入回收站",
        "delete_action_permanent": "已永久删除",
        "delete_action_move_verb": "移入回收站",
        "delete_action_permanent_verb": "永久删除",
        "restore_action": "恢复",
        "purge_from_trash_action": "从回收站永久删除",
        "standalone_gui_description": "启动 manage_codex_sessions 的 Qt GUI。",
        "delete_summary": "{action} {session_count} 个 session，{deleted_file_count} 个 rollout 文件，{removed_index_entry_count} 条索引记录。",
        "confirm_restore_title": "确认恢复",
        "confirm_restore_body": "确认恢复所选 {count} 个 session 吗？",
        "restore_complete_title": "恢复完成",
        "restore_summary": "已恢复 {restored_session_count} 个 session，{restored_file_count} 个 rollout 文件，{restored_index_entry_count} 条索引记录。",
        "restore_summary_skipped": "；跳过冲突 {count} 个：{ids}",
        "confirm_purge_selected_title": "确认永久删除",
        "confirm_purge_selected_body": "确认从回收站永久删除所选 {count} 个 session 吗？该操作不可恢复。",
        "purge_complete_title": "删除完成",
        "purge_summary": "已从回收站永久删除 {session_count} 个 session，{deleted_file_count} 个 rollout 文件。",
        "trash_empty_title": "回收站为空",
        "trash_empty_body": "当前没有可清空的回收站 session。",
        "confirm_purge_all_title": "清空回收站",
        "confirm_purge_all_body": "确认清空回收站中的全部 {count} 个 session 吗？该操作不可恢复。",
        "empty_trash_complete_title": "清空完成",
        "already_running_title": "已在运行",
        "already_running_body": "`manage_codex_sessions` GUI 已在运行，只允许一个实例。",
    },
}

CLI_TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": {
        "parser_description": "Manage local Codex sessions, trash, rename flows, and the Qt UI.",
        "lang_help": "Interface language: system, en, zh-CN. Defaults to CODEX_LANG or the system language.",
        "gui_lang_help": "GUI language: system, en, zh-CN. Defaults to CODEX_UI_LANG, CODEX_LANG, or Simplified Chinese.",
        "codex_home_help": "Codex data directory. Defaults to CODEX_HOME or ~/.codex.",
        "id_help": "Exact match by session id. Can be passed multiple times.",
        "keyword_help": "Fuzzy match by session id, thread name, cwd, or project.",
        "project_help": "Fuzzy match by project path.",
        "cwd_help": "Fuzzy match by cwd.",
        "before_help": "Only match sessions with updated_at earlier than this timestamp, for example 2026-10-01T00:00:00Z.",
        "after_help": "Only match sessions with updated_at later than this timestamp, for example 2026-10-01T00:00:00Z.",
        "missing_files_help": "Only match sessions without rollout files.",
        "with_files_help": "Only match sessions that have rollout files.",
        "limit_help": "Maximum number of sessions to return. Default: {default_limit}; pass -1 for no limit.",
        "query_help": "List active sessions.",
        "trash_help": "List trashed sessions.",
        "projects_help": "Summarize sessions by project.",
        "export_help": "Export one session to Markdown.",
        "rename_help": "Rename a session.",
        "delete_help": "Delete active sessions. Moves them to trash by default.",
        "delete_all_help": "Delete all active sessions. Moves them to trash by default.",
        "restore_help": "Restore sessions from trash.",
        "empty_trash_help": "Permanently delete sessions from trash.",
        "gui_help": "Launch the Qt GUI for managing sessions.",
        "standalone_gui_description": "Launch the manage_codex_sessions Qt GUI.",
        "json_help": "Output JSON.",
        "show_files_help": "Include rollout file paths for each session.",
        "trash_show_files_help": "Include trashed file paths for each session.",
        "projects_trash_help": "Summarize trashed sessions instead of active sessions.",
        "rename_id_help": "Target session id.",
        "export_id_help": "Target session id to export.",
        "export_output_help": "Output Markdown file path. Defaults to ./<session>.md.",
        "export_trash_help": "Export a session from trash.",
        "rename_name_help": "New session name.",
        "rename_trash_help": "Rename a session in trash.",
        "dry_run_help": "Preview sessions and files that would be deleted.",
        "yes_help": "Skip interactive confirmation.",
        "permanent_help": "Delete permanently without moving through trash.",
        "restore_all_help": "Restore all trashed sessions.",
        "empty_trash_all_help": "Permanently delete all trashed sessions.",
        "no_matching_sessions": "No matching sessions.",
        "no_projects": "No projects to display.",
        "header_project": "Project",
        "header_updated": "Updated",
        "header_deleted": "Deleted",
        "header_files": "Files",
        "header_size": "Size",
        "header_source": "Source",
        "header_session_id": "Session ID",
        "header_thread": "Thread",
        "cwd_label": "cwd",
        "file_label": "file",
        "project_column": "Project",
        "sessions_column": "Sessions",
        "delete_action_moved": "Moved to trash",
        "delete_action_permanent": "Permanently deleted",
        "delete_summary": "{action} {session_count} session(s), {deleted_file_count} rollout file(s), and {removed_index_entry_count} index record(s).",
        "restore_summary": "Restored {restored_session_count} session(s), {restored_file_count} rollout file(s), and {restored_index_entry_count} index record(s){suffix}.",
        "restore_summary_skipped": "; skipped {count} conflicted session(s): {ids}",
        "purge_summary": "Permanently deleted {session_count} trashed session(s) and {deleted_file_count} rollout file(s).",
        "confirm_will": "About to {action} these sessions:",
        "confirm_more_sessions": "... {count} more sessions",
        "confirm_prompt": "Continue? Type yes to confirm: ",
        "summary_active": "Total {count} active session(s), CODEX_HOME={codex_home}",
        "summary_trash": "Total {count} trashed session(s), CODEX_HOME={codex_home}",
        "no_delete_targets": "No matching sessions. Nothing was deleted.",
        "dry_run_delete": "dry-run: would {action} {session_count} session(s) and {file_count} rollout file(s).",
        "cancelled": "Operation cancelled.",
        "no_restore_targets": "No matching trashed sessions. Nothing was restored.",
        "no_empty_trash_targets": "No matching trashed sessions. Nothing was permanently deleted.",
        "rename_scope_trash": "trash",
        "rename_scope_active": "active sessions",
        "rename_missing": "Session not found in {scope}: {session_id}",
        "rename_success": "Renamed session {session_id} to: {name}",
        "export_scope_trash": "trash",
        "export_scope_active": "active sessions",
        "export_missing": "Session not found in {scope}: {session_id}",
        "export_success": "Exported session {session_id} to Markdown: {output_path}",
        "qt_missing": "No Qt binding detected. Install PySide6, PyQt6, or PyQt5 first. Detection results: {errors}",
    },
    "zh-CN": {
        "parser_description": "管理本地 Codex sessions、回收站、重命名流程和 Qt 图形界面。",
        "lang_help": "界面语言：system、en、zh-CN。默认读取 CODEX_LANG 或系统语言。",
        "gui_lang_help": "GUI 语言：system、en、zh-CN。默认读取 CODEX_UI_LANG、CODEX_LANG，否则使用简体中文。",
        "codex_home_help": "Codex 数据目录，默认读取 CODEX_HOME 或 ~/.codex。",
        "id_help": "按 session id 精确匹配，可重复传入。",
        "keyword_help": "按 session id、thread name、cwd、project 模糊匹配。",
        "project_help": "按项目路径模糊匹配。",
        "cwd_help": "按 cwd 模糊匹配。",
        "before_help": "仅匹配 updated_at 早于该时间的 session，例如 2026-10-01T00:00:00Z。",
        "after_help": "仅匹配 updated_at 晚于该时间的 session，例如 2026-10-01T00:00:00Z。",
        "missing_files_help": "仅匹配没有 rollout 文件的 session。",
        "with_files_help": "仅匹配存在 rollout 文件的 session。",
        "limit_help": "返回的最大 session 数，默认 {default_limit}；传 -1 表示不限制。",
        "query_help": "查询活动 sessions。",
        "trash_help": "查询回收站 sessions。",
        "projects_help": "按项目统计 sessions。",
        "export_help": "将单个 session 导出为 Markdown。",
        "rename_help": "重命名 session。",
        "delete_help": "删除活动 session，默认移入回收站。",
        "delete_all_help": "删除全部活动 session，默认移入回收站。",
        "restore_help": "从回收站恢复 session。",
        "empty_trash_help": "从回收站永久删除 session。",
        "gui_help": "启动 Qt 图形界面管理 sessions。",
        "standalone_gui_description": "启动 manage_codex_sessions 的 Qt GUI。",
        "json_help": "输出 JSON。",
        "show_files_help": "输出每个 session 对应的 rollout 文件路径。",
        "trash_show_files_help": "输出每个 session 对应的回收站文件路径。",
        "projects_trash_help": "统计回收站中的 sessions。",
        "rename_id_help": "目标 session id。",
        "export_id_help": "要导出的目标 session id。",
        "export_output_help": "输出 Markdown 文件路径；默认写入当前目录下的 ./<session>.md。",
        "export_trash_help": "导出回收站中的 session。",
        "rename_name_help": "新的 session 名称。",
        "rename_trash_help": "重命名回收站中的 session。",
        "dry_run_help": "仅预览将删除的 session 和文件。",
        "yes_help": "跳过交互确认。",
        "permanent_help": "直接永久删除，不经过回收站。",
        "restore_all_help": "恢复回收站全部 session。",
        "empty_trash_all_help": "清空回收站全部 session。",
        "no_matching_sessions": "没有匹配的 sessions。",
        "no_projects": "没有可显示的项目。",
        "header_project": "项目",
        "header_updated": "更新时间",
        "header_deleted": "删除时间",
        "header_files": "文件数",
        "header_size": "大小",
        "header_source": "来源",
        "header_session_id": "Session ID",
        "header_thread": "Thread",
        "cwd_label": "cwd",
        "file_label": "file",
        "project_column": "项目",
        "sessions_column": "Sessions",
        "delete_action_moved": "移入回收站",
        "delete_action_permanent": "已永久删除",
        "delete_summary": "{action} {session_count} 个 session，{deleted_file_count} 个 rollout 文件，{removed_index_entry_count} 条索引记录。",
        "restore_summary": "已恢复 {restored_session_count} 个 session，{restored_file_count} 个 rollout 文件，{restored_index_entry_count} 条索引记录{suffix}。",
        "restore_summary_skipped": "；跳过冲突 {count} 个：{ids}",
        "purge_summary": "已从回收站永久删除 {session_count} 个 session，{deleted_file_count} 个 rollout 文件。",
        "confirm_will": "将要{action}以下 sessions:",
        "confirm_more_sessions": "... 其余 {count} 个 session",
        "confirm_prompt": "继续吗？输入 yes 确认: ",
        "summary_active": "共 {count} 个活动 session，CODEX_HOME={codex_home}",
        "summary_trash": "共 {count} 个回收站 session，CODEX_HOME={codex_home}",
        "no_delete_targets": "没有匹配的 sessions，未执行删除。",
        "dry_run_delete": "dry-run: 将{action} {session_count} 个 session，{file_count} 个 rollout 文件。",
        "cancelled": "已取消操作。",
        "no_restore_targets": "没有匹配的回收站 session，未执行恢复。",
        "no_empty_trash_targets": "没有匹配的回收站 session，未执行清空。",
        "rename_scope_trash": "回收站",
        "rename_scope_active": "活动列表",
        "rename_missing": "未在{scope}找到 session: {session_id}",
        "rename_success": "已将 session {session_id} 重命名为: {name}",
        "export_scope_trash": "回收站",
        "export_scope_active": "活动列表",
        "export_missing": "未在{scope}找到 session: {session_id}",
        "export_success": "已将 session {session_id} 导出为 Markdown: {output_path}",
        "qt_missing": "未检测到 Qt 绑定，请先安装 PySide6、PyQt6 或 PyQt5。当前探测结果: {errors}",
    },
}


def current_system_locale_name() -> str | None:
    try:
        return locale.getlocale()[0]
    except (ValueError, TypeError):
        return None


def normalize_language(
    language: str | None,
    *,
    environment_keys: tuple[str, ...] = ("CODEX_LANG",),
    system_locale_name: str | None = None,
) -> str:
    candidate = language
    if candidate is None:
        for env_name in environment_keys:
            env_value = os.environ.get(env_name)
            if env_value:
                candidate = env_value
                break
    raw = (candidate or "system").strip()
    if not raw or raw.lower() in {"system", "auto", "default"}:
        raw = system_locale_name or current_system_locale_name() or ""
    normalized = raw.lower().replace("_", "-")
    if normalized.startswith("zh"):
        return "zh-CN"
    return "en"


def format_localized_text(
    translations: dict[str, dict[str, str]],
    language: str,
    key: str,
    **kwargs: object,
) -> str:
    templates = translations.get(language, translations["en"])
    template = templates.get(key, translations["en"][key])
    return template.format(**kwargs)


CURRENT_CLI_LANGUAGE = normalize_language(None, environment_keys=("CODEX_LANG",))


def set_cli_language(language: str | None) -> str:
    global CURRENT_CLI_LANGUAGE
    CURRENT_CLI_LANGUAGE = normalize_language(language, environment_keys=("CODEX_LANG",))
    return CURRENT_CLI_LANGUAGE


def cli_text(key: str, **kwargs: object) -> str:
    return format_localized_text(CLI_TRANSLATIONS, CURRENT_CLI_LANGUAGE, key, **kwargs)


def normalize_gui_language(language: str | None, *, system_locale_name: str | None = None) -> str:
    if language is None and not any(os.environ.get(name) for name in ("CODEX_UI_LANG", "CODEX_LANG")):
        return "zh-CN"
    return normalize_language(
        language,
        environment_keys=("CODEX_UI_LANG", "CODEX_LANG"),
        system_locale_name=system_locale_name,
    )


def format_gui_text(language: str, key: str, **kwargs: object) -> str:
    return format_localized_text(GUI_TRANSLATIONS, language, key, **kwargs)


def active_sessions_dir(codex_home: Path) -> Path:
    return codex_home / "sessions"


def trash_root_dir(codex_home: Path) -> Path:
    return codex_home / "session_trash"


def trash_sessions_dir(codex_home: Path) -> Path:
    return trash_root_dir(codex_home) / "sessions"


def trash_manifest_path(codex_home: Path) -> Path:
    return trash_root_dir(codex_home) / "manifest.jsonl"


def read_jsonl_records(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []

    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            raw_line = line.strip()
            if not raw_line:
                continue
            try:
                data = json.loads(raw_line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"failed to parse {path} line {line_no}: {exc}") from exc
            if isinstance(data, dict):
                records.append(data)
    return records


def write_jsonl_records(path: Path, records: Iterable[dict[str, Any]]) -> None:
    ensure_parent_dir(path)
    with path.open("w", encoding="utf-8", newline="") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")))
            handle.write("\n")


@dataclass(slots=True)
class SessionIndexEntry:
    session_id: str
    thread_name: str
    updated_at: datetime | None
    raw: dict[str, Any]


@dataclass(slots=True)
class SessionRollout:
    path: Path
    bytes_size: int
    timestamp: datetime | None
    cwd: str | None
    source: str | None
    cli_version: str | None
    workspace_roots: tuple[str, ...] = ()


@dataclass(slots=True)
class SessionSummary:
    session_id: str
    thread_name: str | None = None
    updated_at: datetime | None = None
    file_count: int = 0
    total_size: int = 0
    cwd_values: set[str] = field(default_factory=set)
    source_values: set[str] = field(default_factory=set)
    cli_versions: set[str] = field(default_factory=set)
    workspace_roots_values: set[str] = field(default_factory=set)
    project_values: set[str] = field(default_factory=set)
    rollout_paths: list[Path] = field(default_factory=list)
    index_entries_raw: list[dict[str, Any]] = field(default_factory=list)
    first_rollout_at: datetime | None = None
    last_rollout_at: datetime | None = None
    deleted_at: datetime | None = None

    def add_index_entry(self, entry: SessionIndexEntry) -> None:
        self.index_entries_raw.append(dict(entry.raw))
        if entry.thread_name and not self.thread_name:
            self.thread_name = entry.thread_name
        if entry.updated_at and (self.updated_at is None or entry.updated_at > self.updated_at):
            self.updated_at = entry.updated_at

    def add_rollout(self, rollout: SessionRollout) -> None:
        self.file_count += 1
        self.total_size += rollout.bytes_size
        self.rollout_paths.append(rollout.path)
        if rollout.cwd:
            self.cwd_values.add(rollout.cwd)
        if rollout.source:
            self.source_values.add(rollout.source)
        if rollout.cli_version:
            self.cli_versions.add(rollout.cli_version)
        if rollout.workspace_roots:
            self.workspace_roots_values.update(rollout.workspace_roots)
            self.project_values.update(rollout.workspace_roots)
        elif rollout.cwd:
            self.project_values.add(rollout.cwd)
        if rollout.timestamp is None:
            return
        if self.first_rollout_at is None or rollout.timestamp < self.first_rollout_at:
            self.first_rollout_at = rollout.timestamp
        if self.last_rollout_at is None or rollout.timestamp > self.last_rollout_at:
            self.last_rollout_at = rollout.timestamp
        if self.updated_at is None or rollout.timestamp > self.updated_at:
            self.updated_at = rollout.timestamp

    @property
    def primary_cwd(self) -> str:
        return sorted(self.cwd_values)[0] if self.cwd_values else "-"

    @property
    def primary_source(self) -> str:
        return sorted(self.source_values)[0] if self.source_values else "-"

    @property
    def primary_project(self) -> str:
        if self.project_values:
            return sorted(self.project_values)[0]
        if self.cwd_values:
            return sorted(self.cwd_values)[0]
        return "-"

    def to_dict(self, include_paths: bool = False) -> dict[str, Any]:
        data: dict[str, Any] = {
            "id": self.session_id,
            "thread_name": self.thread_name,
            "updated_at": isoformat_or_none(self.updated_at),
            "file_count": self.file_count,
            "total_size": self.total_size,
            "cwd_values": sorted(self.cwd_values),
            "source_values": sorted(self.source_values),
            "cli_versions": sorted(self.cli_versions),
            "workspace_roots_values": sorted(self.workspace_roots_values),
            "project_values": sorted(self.project_values),
            "first_rollout_at": isoformat_or_none(self.first_rollout_at),
            "last_rollout_at": isoformat_or_none(self.last_rollout_at),
            "deleted_at": isoformat_or_none(self.deleted_at),
        }
        if include_paths:
            data["rollout_paths"] = [str(path) for path in self.rollout_paths]
        return data


@dataclass(slots=True)
class DeleteResult:
    session_count: int
    deleted_file_count: int
    removed_index_entry_count: int


@dataclass(slots=True)
class RestoreResult:
    restored_session_count: int
    restored_file_count: int
    restored_index_entry_count: int
    skipped_session_ids: list[str] = field(default_factory=list)


@dataclass(slots=True)
class PurgeResult:
    session_count: int
    deleted_file_count: int


def build_session_from_snapshot(
    snapshot: dict[str, Any],
    *,
    deleted_at: datetime | None = None,
    index_entries_raw: list[dict[str, Any]] | None = None,
    rollout_paths: list[Path] | None = None,
) -> SessionSummary:
    summary = SessionSummary(
        session_id=str(snapshot.get("id") or ""),
        thread_name=stringify_metadata(snapshot.get("thread_name")),
        updated_at=parse_iso8601(snapshot.get("updated_at")),
        file_count=int(snapshot.get("file_count") or 0),
        total_size=int(snapshot.get("total_size") or 0),
        deleted_at=deleted_at or parse_iso8601(snapshot.get("deleted_at")),
    )
    summary.cwd_values.update(normalize_string_list(snapshot.get("cwd_values") or []))
    summary.source_values.update(normalize_string_list(snapshot.get("source_values") or []))
    summary.cli_versions.update(normalize_string_list(snapshot.get("cli_versions") or []))
    summary.workspace_roots_values.update(normalize_string_list(snapshot.get("workspace_roots_values") or []))
    summary.project_values.update(normalize_string_list(snapshot.get("project_values") or []))
    summary.first_rollout_at = parse_iso8601(snapshot.get("first_rollout_at"))
    summary.last_rollout_at = parse_iso8601(snapshot.get("last_rollout_at"))
    if not summary.project_values:
        if summary.workspace_roots_values:
            summary.project_values.update(summary.workspace_roots_values)
        elif summary.cwd_values:
            summary.project_values.add(sorted(summary.cwd_values)[0])
    if rollout_paths:
        summary.rollout_paths = rollout_paths
        if not summary.file_count:
            summary.file_count = len(rollout_paths)
    if index_entries_raw:
        summary.index_entries_raw = [dict(item) for item in index_entries_raw]
    return summary


def read_index_entries(index_path: Path) -> list[SessionIndexEntry]:
    records = read_jsonl_records(index_path)
    entries: list[SessionIndexEntry] = []
    for data in records:
        session_id = data.get("id")
        if not session_id:
            continue
        entries.append(
            SessionIndexEntry(
                session_id=str(session_id),
                thread_name=str(data.get("thread_name") or ""),
                updated_at=parse_iso8601(data.get("updated_at")),
                raw=data,
            )
        )
    return entries


def read_first_json_line(path: Path) -> dict[str, Any] | None:
    with path.open("r", encoding="utf-8") as handle:
        first_line = handle.readline().strip()
    if not first_line:
        return None
    data = json.loads(first_line)
    return data if isinstance(data, dict) else None


def scan_rollouts(sessions_dir: Path) -> dict[str, list[SessionRollout]]:
    grouped: dict[str, list[SessionRollout]] = {}
    if not sessions_dir.exists():
        return grouped

    for path in sessions_dir.rglob("*.jsonl"):
        try:
            first_record = read_first_json_line(path)
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(first_record, dict):
            continue
        payload = first_record.get("payload")
        if not isinstance(payload, dict):
            continue

        session_id = payload.get("session_id") or payload.get("id")
        if not session_id:
            continue

        workspace_roots_raw = payload.get("runtime_workspace_roots") or payload.get("workspace_roots") or []
        workspace_roots = tuple(
            normalize_string_list(workspace_roots_raw if isinstance(workspace_roots_raw, list) else [workspace_roots_raw])
        )

        grouped.setdefault(str(session_id), []).append(
            SessionRollout(
                path=path,
                bytes_size=path.stat().st_size,
                timestamp=parse_iso8601(payload.get("timestamp") or first_record.get("timestamp")),
                cwd=stringify_metadata(payload.get("cwd")),
                source=stringify_metadata(payload.get("source")),
                cli_version=stringify_metadata(payload.get("cli_version")),
                workspace_roots=workspace_roots,
            )
        )

    return grouped


def sanitize_filename_component(value: str) -> str:
    collapsed = "_".join(value.split())
    safe = "".join(character if character.isalnum() or character in "-_.()" else "_" for character in collapsed)
    trimmed = safe.strip("._")[:80]
    return trimmed or "session"


def default_session_markdown_filename(session: SessionSummary) -> str:
    label = sanitize_filename_component(session.thread_name or session.session_id)
    session_token = sanitize_filename_component(session.session_id)
    if label != session_token:
        label = f"{label}-{session_token}"
    return f"{label}.md"


def resolve_session_markdown_output_path(session: SessionSummary, output_path: str | Path | None = None) -> Path:
    if output_path is None:
        return Path.cwd() / default_session_markdown_filename(session)
    resolved = Path(output_path).expanduser()
    raw_output = str(output_path)
    if resolved.exists() and resolved.is_dir():
        return resolved / default_session_markdown_filename(session)
    if raw_output.endswith(("/", "\\")):
        return resolved / default_session_markdown_filename(session)
    return resolved


def render_transcript_content_items(items: Iterable[object]) -> str:
    parts: list[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        item_type = str(item.get("type") or "")
        text = item.get("text")
        if isinstance(text, str) and item_type in {"input_text", "output_text", "text", "Text"}:
            stripped = text.strip()
            if stripped:
                parts.append(stripped)
            continue
        location = item.get("path") or item.get("image_url") or item.get("audio_url")
        if isinstance(location, str) and location:
            parts.append(f"[{item_type or 'attachment'}: {location}]")
            continue
        rendered = stringify_metadata(item)
        if rendered:
            parts.append(f"[{item_type}] {rendered}" if item_type else rendered)
    return "\n\n".join(parts).strip()


def collect_session_transcript_messages(session: SessionSummary) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    seen_message_ids: set[str] = set()
    for rollout_path in sorted(session.rollout_paths):
        try:
            records = read_jsonl_records(rollout_path)
        except (OSError, json.JSONDecodeError):
            continue
        for sequence, record in enumerate(records):
            if not isinstance(record, dict) or record.get("type") != "response_item":
                continue
            payload = record.get("payload")
            if not isinstance(payload, dict) or payload.get("type") != "message":
                continue
            role = stringify_metadata(payload.get("role")) or ""
            if role not in {"user", "assistant"}:
                continue
            message_id = stringify_metadata(payload.get("id")) or f"{rollout_path}:{sequence}"
            if message_id in seen_message_ids:
                continue
            content = payload.get("content")
            rendered = render_transcript_content_items(content if isinstance(content, list) else [content])
            if not rendered:
                continue
            seen_message_ids.add(message_id)
            messages.append(
                {
                    "message_id": message_id,
                    "role": role,
                    "timestamp_text": str(record.get("timestamp") or ""),
                    "timestamp": parse_iso8601(record.get("timestamp")),
                    "ordinal": int(record.get("ordinal") or sequence),
                    "text": rendered,
                }
            )
    messages.sort(key=lambda item: (item["timestamp_text"], item["ordinal"], item["message_id"]))
    return messages


def build_session_markdown(session: SessionSummary) -> str:
    title = session.thread_name or session.session_id
    transcript_messages = collect_session_transcript_messages(session)
    lines = [f"# {title}", ""]
    lines.extend(
        [
            f"- Session ID: `{session.session_id}`",
            f"- Thread: {session.thread_name or '-'}",
            f"- Updated: {format_timestamp(session.updated_at)}",
            f"- First Rollout: {format_timestamp(session.first_rollout_at)}",
            f"- Last Rollout: {format_timestamp(session.last_rollout_at)}",
            f"- Project: `{session.primary_project}`",
            f"- CWD: `{session.primary_cwd}`",
            f"- Source: `{session.primary_source}`",
            f"- Rollout Files: {session.file_count}",
            f"- Total Size: {format_bytes(session.total_size)}",
        ]
    )
    if session.deleted_at is not None:
        lines.append(f"- Deleted: {format_timestamp(session.deleted_at)}")
    if session.cli_versions:
        lines.append(f"- CLI Versions: {', '.join(f'`{value}`' for value in sorted(session.cli_versions))}")
    if session.workspace_roots_values:
        lines.append(f"- Workspace Roots: {', '.join(f'`{value}`' for value in sorted(session.workspace_roots_values))}")

    lines.extend(["", "## Transcript", ""])
    if not transcript_messages:
        lines.append("_No exportable user/assistant messages were found in the rollout files._")
    else:
        for message in transcript_messages:
            heading = message["role"].title()
            timestamp = message.get("timestamp")
            if isinstance(timestamp, datetime):
                heading = f"{heading} - {format_timestamp(timestamp)}"
            lines.extend([f"### {heading}", "", str(message["text"]).rstrip(), ""])

    lines.extend(["## Rollout Files", ""])
    if session.rollout_paths:
        lines.extend(f"- `{path}`" for path in sorted(session.rollout_paths))
    else:
        lines.append("- _No rollout files found._")
    return "\n".join(lines).rstrip() + "\n"


def export_session_markdown(session: SessionSummary, output_path: str | Path | None = None) -> Path:
    destination = resolve_session_markdown_output_path(session, output_path)
    ensure_parent_dir(destination)
    destination.write_text(build_session_markdown(session), encoding="utf-8", newline="\n")
    return destination


def find_session_by_id(sessions: Iterable[SessionSummary], session_id: str) -> SessionSummary | None:
    for session in sessions:
        if session.session_id == session_id:
            return session
    return None


def build_session_summaries(codex_home: Path) -> list[SessionSummary]:
    index_entries = read_index_entries(codex_home / "session_index.jsonl")
    rollouts = scan_rollouts(active_sessions_dir(codex_home))

    summaries: dict[str, SessionSummary] = {}
    for entry in index_entries:
        summary = summaries.setdefault(entry.session_id, SessionSummary(session_id=entry.session_id))
        summary.add_index_entry(entry)

    for session_id, files in rollouts.items():
        summary = summaries.setdefault(session_id, SessionSummary(session_id=session_id))
        for rollout in files:
            summary.add_rollout(rollout)

    return sorted(
        summaries.values(),
        key=lambda item: (item.updated_at or datetime.min.replace(tzinfo=timezone.utc), item.session_id),
        reverse=True,
    )


def load_trash_records(codex_home: Path) -> list[dict[str, Any]]:
    return read_jsonl_records(trash_manifest_path(codex_home))


def save_trash_records(codex_home: Path, records: list[dict[str, Any]]) -> None:
    if records:
        write_jsonl_records(trash_manifest_path(codex_home), records)
        return
    manifest = trash_manifest_path(codex_home)
    if manifest.exists():
        manifest.unlink()


def build_trash_summaries(codex_home: Path) -> list[SessionSummary]:
    records = load_trash_records(codex_home)
    summaries: list[SessionSummary] = []
    base_dir = trash_sessions_dir(codex_home)

    for record in records:
        session_snapshot = record.get("session")
        session_id = stringify_metadata(record.get("id"))
        if not isinstance(session_snapshot, dict) or not session_id:
            continue
        rollout_paths = [base_dir / Path(rel_path) for rel_path in normalize_string_list(record.get("rollout_paths") or [])]
        summary = build_session_from_snapshot(
            session_snapshot,
            deleted_at=parse_iso8601(record.get("deleted_at")),
            index_entries_raw=record.get("index_entries") if isinstance(record.get("index_entries"), list) else None,
            rollout_paths=rollout_paths,
        )
        if not summary.session_id:
            summary.session_id = session_id
        summaries.append(summary)

    return sorted(
        summaries,
        key=lambda item: (
            item.deleted_at or datetime.min.replace(tzinfo=timezone.utc),
            item.updated_at or datetime.min.replace(tzinfo=timezone.utc),
            item.session_id,
        ),
        reverse=True,
    )


def parse_multi_value(values: list[str] | None) -> set[str]:
    return {value for value in values or [] if value}


def session_matches_keyword(session: SessionSummary, keyword: str) -> bool:
    lowered = keyword.casefold()
    haystacks = [
        session.session_id,
        session.thread_name or "",
        session.primary_cwd,
        session.primary_source,
        session.primary_project,
        ", ".join(sorted(session.cli_versions)),
    ]
    return any(lowered in item.casefold() for item in haystacks)


def matches_filters(session: SessionSummary, args: argparse.Namespace) -> bool:
    ids = parse_multi_value(getattr(args, "id", None))
    if ids and session.session_id not in ids:
        return False

    keyword = getattr(args, "keyword", None)
    if keyword and not session_matches_keyword(session, keyword):
        return False

    project = getattr(args, "project", None)
    if project:
        wanted = project.casefold()
        projects = session.project_values or ({session.primary_project} if session.primary_project != "-" else set())
        if not any(wanted in item.casefold() for item in projects):
            return False

    cwd = getattr(args, "cwd", None)
    if cwd:
        wanted_cwd = cwd.casefold()
        if not any(wanted_cwd in item.casefold() for item in session.cwd_values):
            return False

    before_value = getattr(args, "before", None)
    if before_value:
        before = parse_iso8601(before_value)
        if before is None or session.updated_at is None or session.updated_at >= before:
            return False

    after_value = getattr(args, "after", None)
    if after_value:
        after = parse_iso8601(after_value)
        if after is None or session.updated_at is None or session.updated_at <= after:
            return False

    if getattr(args, "missing_files", False) and session.file_count > 0:
        return False

    if getattr(args, "with_files", False) and session.file_count == 0:
        return False

    return True


def filter_sessions(summaries: Iterable[SessionSummary], args: argparse.Namespace) -> list[SessionSummary]:
    matches = [summary for summary in summaries if matches_filters(summary, args)]
    limit = getattr(args, "limit", None)
    if limit is None or limit < 0:
        return matches
    return matches[:limit]


def build_project_stats(summaries: Iterable[SessionSummary]) -> list[tuple[str, int]]:
    counts: dict[str, int] = {}
    for summary in summaries:
        project = summary.primary_project
        counts[project] = counts.get(project, 0) + 1
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))


def print_sessions_table(sessions: list[SessionSummary], show_files: bool, *, include_deleted_at: bool = False) -> None:
    if not sessions:
        print(cli_text("no_matching_sessions"))
        return

    headers = [cli_text("header_project"), cli_text("header_updated")]
    if include_deleted_at:
        headers.append(cli_text("header_deleted"))
    headers.extend(
        [
            cli_text("header_files"),
            cli_text("header_size"),
            cli_text("header_source"),
            cli_text("header_session_id"),
            cli_text("header_thread"),
        ]
    )

    rows: list[list[str]] = []
    for session in sessions:
        row = [session.primary_project, format_timestamp(session.updated_at)]
        if include_deleted_at:
            row.append(format_timestamp(session.deleted_at))
        row.extend(
            [
                str(session.file_count),
                format_bytes(session.total_size),
                session.primary_source,
                session.session_id,
                session.thread_name or "-",
            ]
        )
        rows.append(row)

    widths = [len(header) for header in headers]
    max_widths = [36, 24]
    if include_deleted_at:
        max_widths.append(24)
    max_widths.extend([5, 8, 10, 36, 60])

    for row in rows:
        for index, value in enumerate(row):
            widths[index] = min(max(widths[index], len(value)), max_widths[index])

    print("  ".join(header.ljust(widths[index]) for index, header in enumerate(headers)))
    print("  ".join("-" * width for width in widths))

    for session, row in zip(sessions, rows, strict=True):
        print("  ".join(truncate(value, widths[index]).ljust(widths[index]) for index, value in enumerate(row)))
        print(f"    {cli_text('cwd_label')}: {session.primary_cwd}")
        if show_files:
            for path in sorted(session.rollout_paths):
                print(f"    {cli_text('file_label')}: {path}")


def print_sessions_json(sessions: list[SessionSummary], show_files: bool) -> None:
    payload = [session.to_dict(include_paths=show_files) for session in sessions]
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def print_projects_table(stats: list[tuple[str, int]]) -> None:
    if not stats:
        print(cli_text("no_projects"))
        return

    project_header = cli_text("project_column")
    sessions_header = cli_text("sessions_column")
    project_width = max(len(project_header), min(max(len(project) for project, _ in stats), 72))
    count_width = max(len(sessions_header), max(len(str(count)) for _, count in stats))
    print(f"{project_header.ljust(project_width)}  {sessions_header.ljust(count_width)}")
    print(f"{'-' * project_width}  {'-' * count_width}")
    for project, count in stats:
        print(f"{truncate(project, project_width).ljust(project_width)}  {str(count).ljust(count_width)}")


def format_delete_summary(result: DeleteResult, *, moved_to_trash: bool) -> str:
    action = cli_text("delete_action_moved") if moved_to_trash else cli_text("delete_action_permanent")
    return cli_text(
        "delete_summary",
        action=action,
        session_count=result.session_count,
        deleted_file_count=result.deleted_file_count,
        removed_index_entry_count=result.removed_index_entry_count,
    )


def format_restore_summary(result: RestoreResult) -> str:
    suffix = ""
    if result.skipped_session_ids:
        suffix = cli_text(
            "restore_summary_skipped",
            count=len(result.skipped_session_ids),
            ids=", ".join(result.skipped_session_ids),
        )
    return cli_text(
        "restore_summary",
        restored_session_count=result.restored_session_count,
        restored_file_count=result.restored_file_count,
        restored_index_entry_count=result.restored_index_entry_count,
        suffix=suffix,
    )


def format_purge_summary(result: PurgeResult) -> str:
    return cli_text("purge_summary", session_count=result.session_count, deleted_file_count=result.deleted_file_count)


def rewrite_index(index_path: Path, deleted_ids: set[str]) -> int:
    if not index_path.exists():
        return 0

    removed_count = 0
    kept: list[dict[str, Any]] = []
    for record in read_jsonl_records(index_path):
        if stringify_metadata(record.get("id")) in deleted_ids:
            removed_count += 1
            continue
        kept.append(record)
    write_jsonl_records(index_path, kept)
    return removed_count


def append_index_entries(index_path: Path, entries: list[dict[str, Any]]) -> int:
    records = read_jsonl_records(index_path)
    existing_ids = {stringify_metadata(record.get("id")) for record in records}
    appended = 0
    for entry in entries:
        session_id = stringify_metadata(entry.get("id"))
        if not session_id or session_id in existing_ids:
            continue
        records.append(entry)
        existing_ids.add(session_id)
        appended += 1
    write_jsonl_records(index_path, records)
    return appended


def prune_empty_dirs(path: Path, stop_at: Path) -> None:
    current = path
    while current != stop_at and stop_at in current.parents:
        try:
            current.rmdir()
        except OSError:
            break
        current = current.parent


def collect_relative_rollout_paths(codex_home: Path, sessions: list[SessionSummary]) -> dict[str, list[Path]]:
    base_dir = active_sessions_dir(codex_home)
    grouped: dict[str, list[Path]] = {}
    for session in sessions:
        rel_paths: list[Path] = []
        for path in session.rollout_paths:
            try:
                rel_paths.append(path.relative_to(base_dir))
            except ValueError:
                continue
        grouped[session.session_id] = rel_paths
    return grouped


def move_sessions_to_trash(codex_home: Path, sessions: list[SessionSummary]) -> DeleteResult:
    deleted_ids = {session.session_id for session in sessions}
    index_path = codex_home / "session_index.jsonl"
    trash_records = {stringify_metadata(record.get("id")): record for record in load_trash_records(codex_home)}
    rel_rollouts = collect_relative_rollout_paths(codex_home, sessions)

    moved_files = 0
    active_dir = active_sessions_dir(codex_home)
    recycle_dir = trash_sessions_dir(codex_home)
    now = datetime.now(timezone.utc).isoformat()

    for session in sessions:
        stored_rel_paths: list[str] = []
        for rel_path in rel_rollouts.get(session.session_id, []):
            src = active_dir / rel_path
            dest = recycle_dir / rel_path
            if not src.exists():
                continue
            ensure_parent_dir(dest)
            if dest.exists():
                dest.unlink()
            src.replace(dest)
            stored_rel_paths.append(rel_path.as_posix())
            moved_files += 1
            prune_empty_dirs(src.parent, active_dir)

        trash_records[session.session_id] = {
            "id": session.session_id,
            "deleted_at": now,
            "session": session.to_dict(include_paths=False),
            "index_entries": session.index_entries_raw,
            "rollout_paths": stored_rel_paths,
        }

    save_trash_records(codex_home, list(trash_records.values()))
    removed_index_entries = rewrite_index(index_path, deleted_ids)
    return DeleteResult(
        session_count=len(deleted_ids),
        deleted_file_count=moved_files,
        removed_index_entry_count=removed_index_entries,
    )


def delete_active_sessions_forever(codex_home: Path, sessions: list[SessionSummary]) -> DeleteResult:
    deleted_ids = {session.session_id for session in sessions}
    deleted_files = 0
    active_dir = active_sessions_dir(codex_home)

    for session in sessions:
        for path in session.rollout_paths:
            if not path.exists():
                continue
            path.unlink()
            deleted_files += 1
            prune_empty_dirs(path.parent, active_dir)

    removed_index_entries = rewrite_index(codex_home / "session_index.jsonl", deleted_ids)
    return DeleteResult(
        session_count=len(deleted_ids),
        deleted_file_count=deleted_files,
        removed_index_entry_count=removed_index_entries,
    )


def delete_sessions(codex_home: Path, sessions: list[SessionSummary], *, permanent: bool = False) -> DeleteResult:
    if permanent:
        return delete_active_sessions_forever(codex_home, sessions)
    return move_sessions_to_trash(codex_home, sessions)


def restore_sessions_from_trash(codex_home: Path, sessions: list[SessionSummary]) -> RestoreResult:
    records = load_trash_records(codex_home)
    record_map = {stringify_metadata(record.get("id")): record for record in records}
    active_entries = read_index_entries(codex_home / "session_index.jsonl")
    active_ids = {entry.session_id for entry in active_entries}
    active_dir = active_sessions_dir(codex_home)
    recycle_dir = trash_sessions_dir(codex_home)

    restored_files = 0
    restored_index_entries = 0
    restored_sessions = 0
    skipped: list[str] = []
    restored_ids: set[str] = set()

    for session in sessions:
        session_id = session.session_id
        record = record_map.get(session_id)
        if record is None:
            skipped.append(session_id)
            continue
        if session_id in active_ids:
            skipped.append(session_id)
            continue

        rel_paths = [Path(path) for path in normalize_string_list(record.get("rollout_paths") or [])]
        conflict = False
        for rel_path in rel_paths:
            if (active_dir / rel_path).exists():
                conflict = True
                break
        if conflict:
            skipped.append(session_id)
            continue

        index_entries = record.get("index_entries") if isinstance(record.get("index_entries"), list) else []
        if not index_entries:
            snapshot = record.get("session") if isinstance(record.get("session"), dict) else {}
            index_entries = [{
                "id": session_id,
                "thread_name": snapshot.get("thread_name") or "",
                "updated_at": snapshot.get("updated_at"),
            }]
        restored_index_entries += append_index_entries(codex_home / "session_index.jsonl", [dict(item) for item in index_entries])

        for rel_path in rel_paths:
            src = recycle_dir / rel_path
            dest = active_dir / rel_path
            if not src.exists():
                continue
            ensure_parent_dir(dest)
            src.replace(dest)
            restored_files += 1
            prune_empty_dirs(src.parent, recycle_dir)

        restored_sessions += 1
        restored_ids.add(session_id)
        active_ids.add(session_id)

    remaining = [record for record in records if stringify_metadata(record.get("id")) not in restored_ids]
    save_trash_records(codex_home, remaining)
    return RestoreResult(
        restored_session_count=restored_sessions,
        restored_file_count=restored_files,
        restored_index_entry_count=restored_index_entries,
        skipped_session_ids=skipped,
    )


def purge_trashed_sessions(codex_home: Path, sessions: list[SessionSummary]) -> PurgeResult:
    records = load_trash_records(codex_home)
    purge_ids = {session.session_id for session in sessions}
    recycle_dir = trash_sessions_dir(codex_home)
    deleted_files = 0

    remaining: list[dict[str, Any]] = []
    for record in records:
        session_id = stringify_metadata(record.get("id"))
        if session_id not in purge_ids:
            remaining.append(record)
            continue
        for rel_path_text in normalize_string_list(record.get("rollout_paths") or []):
            path = recycle_dir / Path(rel_path_text)
            if not path.exists():
                continue
            path.unlink()
            deleted_files += 1
            prune_empty_dirs(path.parent, recycle_dir)

    save_trash_records(codex_home, remaining)
    return PurgeResult(session_count=len(purge_ids), deleted_file_count=deleted_files)


def rename_session_in_index(index_path: Path, session_id: str, new_name: str) -> int:
    records = read_jsonl_records(index_path)
    changed = 0
    for record in records:
        if stringify_metadata(record.get("id")) != session_id:
            continue
        record["thread_name"] = new_name
        changed += 1
    if changed:
        write_jsonl_records(index_path, records)
    return changed


def rename_trashed_session(codex_home: Path, session_id: str, new_name: str) -> int:
    records = load_trash_records(codex_home)
    changed = 0
    for record in records:
        if stringify_metadata(record.get("id")) != session_id:
            continue
        session_snapshot = record.get("session")
        if isinstance(session_snapshot, dict):
            session_snapshot["thread_name"] = new_name
        index_entries = record.get("index_entries")
        if isinstance(index_entries, list):
            for entry in index_entries:
                if isinstance(entry, dict):
                    entry["thread_name"] = new_name
        changed += 1
    if changed:
        save_trash_records(codex_home, records)
    return changed


def rename_session(codex_home: Path, session_id: str, new_name: str, *, in_trash: bool = False) -> int:
    if in_trash:
        return rename_trashed_session(codex_home, session_id, new_name)
    return rename_session_in_index(codex_home / "session_index.jsonl", session_id, new_name)


def confirm_sessions(action: str, sessions: list[SessionSummary]) -> bool:
    print(cli_text("confirm_will", action=action))
    for session in sessions[:10]:
        print(f"- {session.session_id} | {session.thread_name or '-'}")
    if len(sessions) > 10:
        print(cli_text("confirm_more_sessions", count=len(sessions) - 10))
    answer = input(cli_text("confirm_prompt")).strip()
    return answer == "yes"


def command_query(args: argparse.Namespace) -> int:
    codex_home = resolve_codex_home(args.codex_home)
    sessions = filter_sessions(build_session_summaries(codex_home), args)
    if args.json:
        print_sessions_json(sessions, args.show_files)
    else:
        print_sessions_table(sessions, args.show_files)
        print("\n" + cli_text("summary_active", count=len(sessions), codex_home=codex_home))
    return 0


def command_trash(args: argparse.Namespace) -> int:
    codex_home = resolve_codex_home(args.codex_home)
    sessions = filter_sessions(build_trash_summaries(codex_home), args)
    if args.json:
        print_sessions_json(sessions, args.show_files)
    else:
        print_sessions_table(sessions, args.show_files, include_deleted_at=True)
        print("\n" + cli_text("summary_trash", count=len(sessions), codex_home=codex_home))
    return 0


def command_projects(args: argparse.Namespace) -> int:
    codex_home = resolve_codex_home(args.codex_home)
    sessions = build_trash_summaries(codex_home) if args.trash else build_session_summaries(codex_home)
    stats = build_project_stats(filter_sessions(sessions, args))
    if args.json:
        payload = [{"project": project, "session_count": count} for project, count in stats]
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print_projects_table(stats)
    return 0


def execute_delete(codex_home: Path, sessions: list[SessionSummary], *, dry_run: bool, yes: bool, permanent: bool) -> int:
    if not sessions:
        print(cli_text("no_delete_targets"))
        return 0

    if dry_run:
        rollout_paths = {path for session in sessions for path in session.rollout_paths}
        action = cli_text("delete_action_permanent_verb") if permanent else cli_text("delete_action_move_verb")
        print(cli_text("dry_run_delete", action=action, session_count=len(sessions), file_count=len(rollout_paths)))
        print_sessions_table(sessions, show_files=True)
        return 0

    action = cli_text("delete_action_permanent_verb") if permanent else cli_text("delete_action_move_verb")
    if not yes and not confirm_sessions(action, sessions):
        print(cli_text("cancelled"))
        return 1

    result = delete_sessions(codex_home, sessions, permanent=permanent)
    print(format_delete_summary(result, moved_to_trash=not permanent))
    return 0


def command_delete(args: argparse.Namespace) -> int:
    codex_home = resolve_codex_home(args.codex_home)
    sessions = filter_sessions(build_session_summaries(codex_home), args)
    return execute_delete(codex_home, sessions, dry_run=args.dry_run, yes=args.yes, permanent=args.permanent)


def command_delete_all(args: argparse.Namespace) -> int:
    codex_home = resolve_codex_home(args.codex_home)
    sessions = build_session_summaries(codex_home)
    return execute_delete(codex_home, sessions, dry_run=args.dry_run, yes=args.yes, permanent=args.permanent)


def command_restore(args: argparse.Namespace) -> int:
    codex_home = resolve_codex_home(args.codex_home)
    sessions = build_trash_summaries(codex_home)
    targets = sessions if args.all else filter_sessions(sessions, args)
    if not targets:
        print(cli_text("no_restore_targets"))
        return 0
    if not args.yes and not confirm_sessions(cli_text("restore_action"), targets):
        print(cli_text("cancelled"))
        return 1
    result = restore_sessions_from_trash(codex_home, targets)
    print(format_restore_summary(result))
    return 0


def command_empty_trash(args: argparse.Namespace) -> int:
    codex_home = resolve_codex_home(args.codex_home)
    sessions = build_trash_summaries(codex_home)
    targets = sessions if args.all else filter_sessions(sessions, args)
    if not targets:
        print(cli_text("no_empty_trash_targets"))
        return 0
    if not args.yes and not confirm_sessions(cli_text("purge_from_trash_action"), targets):
        print(cli_text("cancelled"))
        return 1
    result = purge_trashed_sessions(codex_home, targets)
    print(format_purge_summary(result))
    return 0


def command_rename(args: argparse.Namespace) -> int:
    codex_home = resolve_codex_home(args.codex_home)
    changed = rename_session(codex_home, args.id, args.name, in_trash=args.trash)
    if not changed:
        scope = cli_text("rename_scope_trash") if args.trash else cli_text("rename_scope_active")
        print(cli_text("rename_missing", scope=scope, session_id=args.id))
        return 1
    print(cli_text("rename_success", session_id=args.id, name=args.name))
    return 0


def command_export(args: argparse.Namespace) -> int:
    codex_home = resolve_codex_home(args.codex_home)
    sessions = build_trash_summaries(codex_home) if args.trash else build_session_summaries(codex_home)
    session = find_session_by_id(sessions, args.id)
    if session is None:
        scope = cli_text("export_scope_trash") if args.trash else cli_text("export_scope_active")
        print(cli_text("export_missing", scope=scope, session_id=args.id))
        return 1
    output_path = export_session_markdown(session, args.output)
    print(cli_text("export_success", session_id=session.session_id, output_path=output_path))
    return 0


def load_qt_binding() -> tuple[str, Any, Any, Any]:
    candidates = ("PySide6", "PyQt6", "PyQt5")
    errors: list[str] = []
    for name in candidates:
        try:
            if name == "PySide6":
                from PySide6 import QtCore, QtGui, QtWidgets  # type: ignore
            elif name == "PyQt6":
                from PyQt6 import QtCore, QtGui, QtWidgets  # type: ignore
            else:
                from PyQt5 import QtCore, QtGui, QtWidgets  # type: ignore
            return name, QtCore, QtGui, QtWidgets
        except ImportError as exc:
            errors.append(f"{name}: {exc}")
    raise RuntimeError(cli_text("qt_missing", errors="; ".join(errors)))


def launch_gui(codex_home: Path, *, language: str | None = None) -> int:
    binding_name, QtCore, QtGui, QtWidgets = load_qt_binding()
    qlocale = getattr(QtCore, "QLocale", None)
    system_locale_name = qlocale.system().name() if qlocale and hasattr(qlocale, "system") else None
    ui_language = normalize_gui_language(language, system_locale_name=system_locale_name)

    resize_mode = getattr(QtWidgets.QHeaderView, "ResizeMode", QtWidgets.QHeaderView)
    selection_mode = getattr(QtWidgets.QAbstractItemView, "SelectionMode", QtWidgets.QAbstractItemView)
    selection_behavior = getattr(QtWidgets.QAbstractItemView, "SelectionBehavior", QtWidgets.QAbstractItemView)
    edit_trigger = getattr(QtWidgets.QAbstractItemView, "EditTrigger", QtWidgets.QAbstractItemView)
    message_buttons = getattr(QtWidgets.QMessageBox, "StandardButton", QtWidgets.QMessageBox)
    sort_order = getattr(QtCore.Qt, "SortOrder", QtCore.Qt)
    alignment_flag = getattr(QtCore.Qt, "AlignmentFlag", QtCore.Qt)
    context_menu_policy = getattr(QtCore.Qt, "ContextMenuPolicy", QtCore.Qt)
    shortcut_context = getattr(QtCore.Qt, "ShortcutContext", QtCore.Qt)
    widget_attribute = getattr(QtCore.Qt, "WidgetAttribute", QtCore.Qt)

    def t(key: str, **kwargs: object) -> str:
        return format_gui_text(ui_language, key, **kwargs)

    def format_delete_summary_gui(result: DeleteResult, *, moved_to_trash: bool) -> str:
        action = t("delete_action_moved") if moved_to_trash else t("delete_action_permanent")
        return t(
            "delete_summary",
            action=action,
            session_count=result.session_count,
            deleted_file_count=result.deleted_file_count,
            removed_index_entry_count=result.removed_index_entry_count,
        )

    def format_restore_summary_gui(result: RestoreResult) -> str:
        suffix = ""
        if result.skipped_session_ids:
            suffix = t(
                "restore_summary_skipped",
                count=len(result.skipped_session_ids),
                ids=", ".join(result.skipped_session_ids),
            )
        return (
            t(
                "restore_summary",
                restored_session_count=result.restored_session_count,
                restored_file_count=result.restored_file_count,
                restored_index_entry_count=result.restored_index_entry_count,
            )
            + suffix
        )

    def format_purge_summary_gui(result: PurgeResult) -> str:
        return t("purge_summary", session_count=result.session_count, deleted_file_count=result.deleted_file_count)

    def acquire_gui_instance_lock() -> Any | None:
        lock_path = Path(QtCore.QDir.tempPath()) / "manage_codex_sessions_gui.lock"
        ensure_parent_dir(lock_path)
        lock_file = QtCore.QLockFile(str(lock_path))
        if hasattr(lock_file, "setStaleLockTime"):
            lock_file.setStaleLockTime(60 * 1000)
        if not lock_file.tryLock(0):
            return None
        return lock_file

    class SessionPanel(QtWidgets.QWidget):
        def __init__(self, *, include_deleted_at: bool, button_specs: list[tuple[str, str]], title_key: str) -> None:
            super().__init__()
            self.include_deleted_at = include_deleted_at
            self.title_key = title_key
            self.title = t(title_key)
            self.all_sessions: list[SessionSummary] = []
            self.visible_sessions: list[SessionSummary] = []
            self.session_by_id: dict[str, SessionSummary] = {}
            self.on_state_changed: Any = None
            self.on_thread_double_clicked: Any = None
            self.on_rename_requested: Any = None
            self.on_export_markdown_requested: Any = None
            self.on_session_ids_copied: Any = None

            layout = QtWidgets.QVBoxLayout(self)

            filter_layout = QtWidgets.QHBoxLayout()
            self.project_label = QtWidgets.QLabel(t("filter_project_label"))
            filter_layout.addWidget(self.project_label)
            self.project_combo = QtWidgets.QComboBox()
            self.project_combo.addItem(t("all_projects"), "")
            filter_layout.addWidget(self.project_combo)
            self.search_label = QtWidgets.QLabel(t("filter_search_label"))
            filter_layout.addWidget(self.search_label)
            self.filter_edit = QtWidgets.QLineEdit()
            self.filter_edit.setPlaceholderText(t("filter_placeholder"))
            filter_layout.addWidget(self.filter_edit, 1)
            layout.addLayout(filter_layout)

            headers = [t("header_project"), t("header_updated")]
            if self.include_deleted_at:
                headers.append(t("header_deleted"))
            headers.extend(
                [
                    t("header_files"),
                    t("header_size"),
                    t("header_source"),
                    t("header_session_id"),
                    t("header_thread"),
                    t("header_cwd"),
                ]
            )
            self.session_id_column = headers.index(t("header_session_id"))
            self.thread_column = headers.index(t("header_thread"))

            self.table = QtWidgets.QTableWidget(0, len(headers))
            self.table.setHorizontalHeaderLabels(headers)
            self.table.setSelectionBehavior(selection_behavior.SelectRows)
            self.table.setSelectionMode(selection_mode.ExtendedSelection)
            self.table.setEditTriggers(edit_trigger.NoEditTriggers)
            self.table.setAlternatingRowColors(True)
            self.table.setSortingEnabled(True)
            self.table.verticalHeader().setVisible(False)
            self.table.setContextMenuPolicy(context_menu_policy.CustomContextMenu)
            header = self.table.horizontalHeader()
            for column in range(len(headers)):
                mode = resize_mode.ResizeToContents if column < len(headers) - 2 else resize_mode.Stretch
                header.setSectionResizeMode(column, mode)
            layout.addWidget(self.table, 1)

            copy_key_sequence = QtGui.QKeySequence.StandardKey.Copy
            self.copy_session_id_shortcut = QtGui.QShortcut(copy_key_sequence, self.table)
            if hasattr(self.copy_session_id_shortcut, "setContext"):
                self.copy_session_id_shortcut.setContext(shortcut_context.WidgetShortcut)
            self.copy_session_id_shortcut.activated.connect(self.copy_selected_or_current_session_ids)

            button_layout = QtWidgets.QHBoxLayout()
            self.buttons: dict[str, Any] = {}
            self.button_label_keys = {key: label_key for key, label_key in button_specs}
            for key, label_key in button_specs:
                button = QtWidgets.QPushButton(t(label_key))
                self.buttons[key] = button
                button_layout.addWidget(button)
            button_layout.addStretch(1)
            layout.addLayout(button_layout)

            self.project_combo.currentIndexChanged.connect(self.apply_filter)
            self.filter_edit.textChanged.connect(self.apply_filter)
            self.table.itemSelectionChanged.connect(self._notify_state_changed)
            self.table.itemDoubleClicked.connect(self._handle_item_double_clicked)
            self.table.customContextMenuRequested.connect(self._show_table_context_menu)

            if "select_all" in self.buttons:
                self.buttons["select_all"].clicked.connect(self.select_all_rows)
            if "clear_selection" in self.buttons:
                self.buttons["clear_selection"].clicked.connect(self.clear_selection)
            if "copy_session_id" in self.buttons:
                self.buttons["copy_session_id"].clicked.connect(self.copy_selected_or_current_session_ids)

        def _notify_state_changed(self) -> None:
            if callable(self.on_state_changed):
                self.on_state_changed()

        def _handle_item_double_clicked(self, item: Any) -> None:
            if item is None:
                return
            if item.column() == self.session_id_column:
                self.copy_session_id_for_row(item.row())
                return
            if item.column() != self.thread_column:
                return
            session = self.session_for_row(item.row())
            if session is None:
                return
            if callable(self.on_thread_double_clicked):
                self.on_thread_double_clicked(session)

        def copy_session_id_for_row(self, row: int) -> bool:
            session = self.session_for_row(row)
            if session is None:
                return False
            return self.copy_session_ids([session.session_id])

        def copy_session_ids(self, session_ids: list[str]) -> bool:
            clipboard = QtWidgets.QApplication.clipboard()
            if clipboard is None:
                return False
            unique_session_ids = list(dict.fromkeys(session_ids))
            if not unique_session_ids:
                return False
            clipboard.setText("\n".join(unique_session_ids))
            if callable(self.on_session_ids_copied):
                self.on_session_ids_copied(unique_session_ids)
            return True

        def copy_selected_or_current_session_ids(self) -> None:
            model = self.table.selectionModel()
            if model is not None:
                selected_session_ids: list[str] = []
                seen_rows: set[int] = set()
                for selected_index in model.selectedRows():
                    row = selected_index.row()
                    if row in seen_rows:
                        continue
                    session = self.session_for_row(row)
                    if session is not None:
                        selected_session_ids.append(session.session_id)
                        seen_rows.add(row)
                if selected_session_ids:
                    self.copy_session_ids(selected_session_ids)
                    return
            current_row = self.table.currentRow()
            if current_row >= 0:
                self.copy_session_id_for_row(current_row)

        def _show_table_context_menu(self, position: Any) -> None:
            index = self.table.indexAt(position)
            target_session: SessionSummary | None = None
            if index.isValid():
                model = self.table.selectionModel()
                selected_rows = {selected_index.row() for selected_index in model.selectedRows()} if model is not None else set()
                if index.row() not in selected_rows:
                    self.table.selectRow(index.row())
                self.table.setCurrentCell(index.row(), self.session_id_column)
                target_session = self.session_for_row(index.row())
            menu = QtWidgets.QMenu(self.table)
            copy_action = menu.addAction(t("copy_session_id_action"))
            copy_action.triggered.connect(self.copy_selected_or_current_session_ids)
            if target_session is not None:
                rename_action = menu.addAction(t("rename"))
                rename_action.triggered.connect(lambda checked=False, session=target_session: self.request_rename(session))
                export_action = menu.addAction(t("export_markdown"))
                export_action.triggered.connect(lambda checked=False, session=target_session: self.request_export_markdown(session))
            menu.exec(self.table.viewport().mapToGlobal(position))

        def request_rename(self, session: SessionSummary) -> None:
            if callable(self.on_rename_requested):
                self.on_rename_requested(session)

        def request_export_markdown(self, session: SessionSummary) -> None:
            if callable(self.on_export_markdown_requested):
                self.on_export_markdown_requested(session)

        def set_sessions(self, sessions: list[SessionSummary]) -> None:
            self.all_sessions = list(sessions)
            self.session_by_id = {session.session_id: session for session in sessions}
            self.refresh_project_options()
            self.apply_filter()

        def retranslate(self) -> None:
            self.title = t(self.title_key)
            self.project_label.setText(t("filter_project_label"))
            self.search_label.setText(t("filter_search_label"))
            self.filter_edit.setPlaceholderText(t("filter_placeholder"))
            headers = [t("header_project"), t("header_updated")]
            if self.include_deleted_at:
                headers.append(t("header_deleted"))
            headers.extend(
                [
                    t("header_files"),
                    t("header_size"),
                    t("header_source"),
                    t("header_session_id"),
                    t("header_thread"),
                    t("header_cwd"),
                ]
            )
            self.session_id_column = headers.index(t("header_session_id"))
            self.thread_column = headers.index(t("header_thread"))
            self.table.setHorizontalHeaderLabels(headers)
            for key, label_key in self.button_label_keys.items():
                self.buttons[key].setText(t(label_key))
            self.refresh_project_options()
            self.populate_table()

        def refresh_project_options(self) -> None:
            current_value = self.project_combo.currentData()
            projects = sorted({session.primary_project for session in self.all_sessions})
            self.project_combo.blockSignals(True)
            self.project_combo.clear()
            self.project_combo.addItem(t("all_projects"), "")
            for project in projects:
                label = t("unknown_project") if project == "-" else project
                self.project_combo.addItem(label, project)
            index = self.project_combo.findData(current_value)
            self.project_combo.setCurrentIndex(index if index >= 0 else 0)
            self.project_combo.blockSignals(False)

        def apply_filter(self) -> None:
            keyword = self.filter_edit.text().strip()
            project = self.project_combo.currentData()
            visible = self.all_sessions
            if project:
                visible = [session for session in visible if session.primary_project == project]
            if keyword:
                visible = [session for session in visible if session_matches_keyword(session, keyword)]
            self.visible_sessions = visible
            self.populate_table()
            self._notify_state_changed()

        def populate_table(self) -> None:
            self.table.setSortingEnabled(False)
            self.table.clearContents()
            self.table.setRowCount(len(self.visible_sessions))

            for row, session in enumerate(self.visible_sessions):
                project_value = t("unknown_project") if session.primary_project == "-" else session.primary_project
                values = [project_value, format_timestamp(session.updated_at)]
                if self.include_deleted_at:
                    values.append(format_timestamp(session.deleted_at))
                values.extend([
                    str(session.file_count),
                    format_bytes(session.total_size),
                    session.primary_source,
                    session.session_id,
                    session.thread_name or "-",
                    session.primary_cwd,
                ])
                for column, value in enumerate(values):
                    item = QtWidgets.QTableWidgetItem(value)
                    item.setToolTip(value)
                    self.table.setItem(row, column, item)

            self.table.setSortingEnabled(True)
            sort_column = 2 if self.include_deleted_at else 1
            self.table.sortItems(sort_column, sort_order.DescendingOrder)

        def session_for_row(self, row: int) -> SessionSummary | None:
            item = self.table.item(row, self.session_id_column)
            if item is None:
                return None
            return self.session_by_id.get(item.text())

        def selected_sessions(self) -> list[SessionSummary]:
            model = self.table.selectionModel()
            if model is None:
                return []
            sessions: list[SessionSummary] = []
            seen_ids: set[str] = set()
            for index in model.selectedRows():
                session = self.session_for_row(index.row())
                if session is None or session.session_id in seen_ids:
                    continue
                sessions.append(session)
                seen_ids.add(session.session_id)
            return sessions

        def select_all_rows(self) -> None:
            self.table.selectAll()
            self._notify_state_changed()

        def clear_selection(self) -> None:
            self.table.clearSelection()
            self._notify_state_changed()

    class SessionManagerWindow(QtWidgets.QWidget):
        def __init__(self, initial_codex_home: Path) -> None:
            super().__init__()
            self.current_codex_home = initial_codex_home
            self.active_sessions: list[SessionSummary] = []
            self.trash_sessions: list[SessionSummary] = []
            self.toast_timer = QtCore.QTimer(self)
            self.toast_timer.setSingleShot(True)
            self.toast_timer.timeout.connect(self.hide_toast)

            self.setWindowTitle(t("window_title"))
            self.resize(1420, 860)

            root_layout = QtWidgets.QVBoxLayout(self)

            path_layout = QtWidgets.QHBoxLayout()
            self.codex_home_label = QtWidgets.QLabel("CODEX_HOME")
            path_layout.addWidget(self.codex_home_label)
            self.codex_home_edit = QtWidgets.QLineEdit(str(initial_codex_home))
            path_layout.addWidget(self.codex_home_edit, 1)
            self.browse_button = QtWidgets.QPushButton(t("browse"))
            self.refresh_button = QtWidgets.QPushButton(t("refresh"))
            path_layout.addWidget(self.browse_button)
            path_layout.addWidget(self.refresh_button)
            self.language_label = QtWidgets.QLabel(t("language_label"))
            path_layout.addWidget(self.language_label)
            self.language_combo = QtWidgets.QComboBox()
            path_layout.addWidget(self.language_combo)
            root_layout.addLayout(path_layout)

            self.info_label = QtWidgets.QLabel(t("qt_backend", binding_name=binding_name))
            root_layout.addWidget(self.info_label)

            self.tabs = QtWidgets.QTabWidget()
            self.active_panel = SessionPanel(
                include_deleted_at=False,
                title_key="active_title",
                button_specs=[
                    ("select_all", "select_all"),
                    ("clear_selection", "clear_selection"),
                    ("copy_session_id", "copy_session_id_action"),
                    ("export_markdown", "export_markdown"),
                    ("rename", "rename"),
                    ("delete", "delete_to_trash"),
                ],
            )
            self.trash_panel = SessionPanel(
                include_deleted_at=True,
                title_key="trash_title",
                button_specs=[
                    ("select_all", "select_all"),
                    ("clear_selection", "clear_selection"),
                    ("copy_session_id", "copy_session_id_action"),
                    ("export_markdown", "export_markdown"),
                    ("rename", "rename"),
                    ("restore", "restore_selected"),
                    ("purge_selected", "purge_selected"),
                    ("purge_all", "purge_all"),
                ],
            )
            self.tabs.addTab(self.active_panel, t("active_title"))
            self.tabs.addTab(self.trash_panel, t("trash_title"))
            root_layout.addWidget(self.tabs, 1)

            self.status_label = QtWidgets.QLabel(t("ready"))
            root_layout.addWidget(self.status_label)

            self.toast_label = QtWidgets.QLabel("", self)
            self.toast_label.hide()
            self.toast_label.setAlignment(alignment_flag.AlignCenter)
            self.toast_label.setMargin(8)
            self.toast_label.setStyleSheet(
                "QLabel {"
                "background-color: rgba(32, 32, 32, 220);"
                "color: white;"
                "border-radius: 8px;"
                "font-weight: 600;"
                "}"
            )
            if hasattr(self.toast_label, "setAttribute"):
                self.toast_label.setAttribute(widget_attribute.WA_TransparentForMouseEvents, True)

            self.browse_button.clicked.connect(self.choose_codex_home)
            self.refresh_button.clicked.connect(self.reload_all)
            self.language_combo.currentIndexChanged.connect(self.change_gui_language_from_picker)
            self.tabs.currentChanged.connect(self.update_status)
            self.active_panel.on_state_changed = self.update_status
            self.trash_panel.on_state_changed = self.update_status
            self.active_panel.on_thread_double_clicked = self.rename_active_session
            self.trash_panel.on_thread_double_clicked = self.rename_trash_session
            self.active_panel.on_rename_requested = self.rename_active_session
            self.trash_panel.on_rename_requested = self.rename_trash_session
            self.active_panel.on_export_markdown_requested = self.export_active_session
            self.trash_panel.on_export_markdown_requested = self.export_trash_session
            self.active_panel.on_session_ids_copied = self.handle_session_ids_copied
            self.trash_panel.on_session_ids_copied = self.handle_session_ids_copied

            self.active_panel.buttons["rename"].clicked.connect(self.rename_active_selected)
            self.active_panel.buttons["export_markdown"].clicked.connect(self.export_active_selected)
            self.active_panel.buttons["delete"].clicked.connect(self.delete_active_selected)
            self.trash_panel.buttons["rename"].clicked.connect(self.rename_trash_selected)
            self.trash_panel.buttons["export_markdown"].clicked.connect(self.export_trash_selected)
            self.trash_panel.buttons["restore"].clicked.connect(self.restore_trash_selected)
            self.trash_panel.buttons["purge_selected"].clicked.connect(self.purge_trash_selected)
            self.trash_panel.buttons["purge_all"].clicked.connect(self.purge_trash_all)

            self.refresh_language_options()
            self.reload_all()

        def refresh_language_options(self) -> None:
            self.language_combo.blockSignals(True)
            self.language_combo.clear()
            self.language_combo.addItem(t("language_option_zh_cn"), "zh-CN")
            self.language_combo.addItem(t("language_option_en"), "en")
            index = self.language_combo.findData(ui_language)
            self.language_combo.setCurrentIndex(index if index >= 0 else 0)
            self.language_combo.blockSignals(False)

        def change_gui_language_from_picker(self) -> None:
            selected = self.language_combo.currentData()
            if selected:
                self.set_gui_language(str(selected))

        def set_gui_language(self, language_code: str) -> None:
            nonlocal ui_language
            normalized = normalize_gui_language(language_code, system_locale_name=system_locale_name)
            if normalized == ui_language:
                return
            ui_language = normalized
            self.retranslate_ui()

        def retranslate_ui(self) -> None:
            self.setWindowTitle(t("window_title"))
            self.browse_button.setText(t("browse"))
            self.refresh_button.setText(t("refresh"))
            self.language_label.setText(t("language_label"))
            self.info_label.setText(t("qt_backend", binding_name=binding_name))
            self.refresh_language_options()
            self.active_panel.retranslate()
            self.trash_panel.retranslate()
            self.tabs.setTabText(self.tabs.indexOf(self.active_panel), t("active_title"))
            self.tabs.setTabText(self.tabs.indexOf(self.trash_panel), t("trash_title"))
            self.update_status()

        def resolve_current_codex_home(self) -> Path:
            return resolve_codex_home(self.codex_home_edit.text().strip() or None)

        def choose_codex_home(self) -> None:
            selected = QtWidgets.QFileDialog.getExistingDirectory(self, t("choose_codex_home"), self.codex_home_edit.text())
            if not selected:
                return
            self.codex_home_edit.setText(selected)
            self.reload_all()

        def reload_all(self) -> None:
            try:
                codex_home = self.resolve_current_codex_home()
                active = build_session_summaries(codex_home)
                trash = build_trash_summaries(codex_home)
            except Exception as exc:
                QtWidgets.QMessageBox.critical(self, t("load_failed_title"), str(exc))
                return
            self.current_codex_home = codex_home
            self.active_sessions = active
            self.trash_sessions = trash
            self.active_panel.set_sessions(active)
            self.trash_panel.set_sessions(trash)
            self.update_status()

        def update_status(self) -> None:
            current_panel = self.active_panel if self.tabs.currentWidget() is self.active_panel else self.trash_panel
            selected_count = len(current_panel.selected_sessions())
            visible_count = len(current_panel.visible_sessions)
            title = current_panel.title
            self.status_label.setText(
                t(
                    "status_summary",
                    codex_home=self.current_codex_home,
                    active_count=len(self.active_sessions),
                    trash_count=len(self.trash_sessions),
                    title=title,
                    visible_count=visible_count,
                    selected_count=selected_count,
                )
            )

        def position_toast(self) -> None:
            self.toast_label.adjustSize()
            margin = 16
            status_geometry = self.status_label.geometry()
            x = max(margin, self.width() - self.toast_label.width() - margin)
            if status_geometry.isValid():
                y = max(margin, status_geometry.top() - self.toast_label.height() - 12)
            else:
                y = max(margin, self.height() - self.toast_label.height() - margin)
            self.toast_label.move(x, y)

        def show_toast(self, message: str, *, timeout_ms: int = 2000) -> None:
            self.toast_label.setText(message)
            self.position_toast()
            self.toast_label.show()
            self.toast_label.raise_()
            self.toast_timer.start(timeout_ms)

        def hide_toast(self) -> None:
            self.toast_timer.stop()
            self.toast_label.hide()

        def handle_session_ids_copied(self, session_ids: list[str]) -> None:
            if len(session_ids) == 1:
                self.show_toast(t("copy_session_id_body"))
                return
            self.show_toast(t("copy_session_ids_body", count=len(session_ids)))

        def resizeEvent(self, event: Any) -> None:
            super().resizeEvent(event)
            if self.toast_label.isVisible():
                self.position_toast()

        def prompt_new_name(self, current_name: str) -> str | None:
            text, accepted = QtWidgets.QInputDialog.getText(
                self,
                t("rename_session_title"),
                t("rename_session_label"),
                text=current_name,
            )
            if not accepted:
                return None
            value = text.strip()
            return value or None

        def prompt_export_path(self, session: SessionSummary) -> Path | None:
            default_path = self.current_codex_home / default_session_markdown_filename(session)
            selected, _selected_filter = QtWidgets.QFileDialog.getSaveFileName(
                self,
                t("export_markdown_title"),
                str(default_path),
                t("export_markdown_filter"),
            )
            if not selected:
                return None
            return Path(selected)

        def export_one_session(self, session: SessionSummary) -> None:
            output_path = self.prompt_export_path(session)
            if output_path is None:
                return
            try:
                written_path = export_session_markdown(session, output_path)
            except Exception as exc:
                QtWidgets.QMessageBox.critical(self, t("export_failed_title"), str(exc))
                return
            QtWidgets.QMessageBox.information(
                self,
                t("export_complete_title"),
                t("export_complete_body", output_path=written_path),
            )

        def export_selected(self, *, in_trash: bool) -> None:
            panel = self.trash_panel if in_trash else self.active_panel
            sessions = panel.selected_sessions()
            if len(sessions) != 1:
                QtWidgets.QMessageBox.information(
                    self,
                    t("export_single_select_title"),
                    t("export_single_select_body"),
                )
                return
            self.export_one_session(sessions[0])

        def rename_one_session(self, session: SessionSummary, *, in_trash: bool) -> None:
            new_name = self.prompt_new_name(session.thread_name or "")
            if not new_name:
                return
            changed = rename_session(self.current_codex_home, session.session_id, new_name, in_trash=in_trash)
            if not changed:
                QtWidgets.QMessageBox.warning(
                    self,
                    t("rename_failed_title"),
                    t("rename_missing_session", session_id=session.session_id),
                )
                return
            self.reload_all()

        def rename_selected(self, *, in_trash: bool) -> None:
            panel = self.trash_panel if in_trash else self.active_panel
            sessions = panel.selected_sessions()
            if len(sessions) != 1:
                QtWidgets.QMessageBox.information(
                    self,
                    t("rename_single_select_title"),
                    t("rename_single_select_body"),
                )
                return
            self.rename_one_session(sessions[0], in_trash=in_trash)

        def rename_active_selected(self) -> None:
            self.rename_selected(in_trash=False)

        def rename_trash_selected(self) -> None:
            self.rename_selected(in_trash=True)

        def export_active_selected(self) -> None:
            self.export_selected(in_trash=False)

        def export_trash_selected(self) -> None:
            self.export_selected(in_trash=True)

        def export_active_session(self, session: SessionSummary) -> None:
            self.export_one_session(session)

        def export_trash_session(self, session: SessionSummary) -> None:
            self.export_one_session(session)

        def rename_active_session(self, session: SessionSummary) -> None:
            self.rename_one_session(session, in_trash=False)

        def rename_trash_session(self, session: SessionSummary) -> None:
            self.rename_one_session(session, in_trash=True)

        def delete_active_selected(self) -> None:
            sessions = self.active_panel.selected_sessions()
            if not sessions:
                QtWidgets.QMessageBox.information(self, t("no_selection_title"), t("select_active_first"))
                return
            preview = [f"- {session.session_id} | {session.thread_name or '-'}" for session in sessions[:8]]
            if len(sessions) > 8:
                preview.append(t("more_sessions", count=len(sessions) - 8))
            reply = QtWidgets.QMessageBox.question(
                self,
                t("confirm_delete_title"),
                t("confirm_delete_body", preview="\n".join(preview)),
                message_buttons.Yes | message_buttons.No,
                message_buttons.No,
            )
            if reply != message_buttons.Yes:
                return
            result = move_sessions_to_trash(self.current_codex_home, sessions)
            QtWidgets.QMessageBox.information(
                self,
                t("delete_complete_title"),
                format_delete_summary_gui(result, moved_to_trash=True),
            )
            self.reload_all()

        def restore_trash_selected(self) -> None:
            sessions = self.trash_panel.selected_sessions()
            if not sessions:
                QtWidgets.QMessageBox.information(self, t("no_selection_title"), t("select_trash_first"))
                return
            reply = QtWidgets.QMessageBox.question(
                self,
                t("confirm_restore_title"),
                t("confirm_restore_body", count=len(sessions)),
                message_buttons.Yes | message_buttons.No,
                message_buttons.Yes,
            )
            if reply != message_buttons.Yes:
                return
            result = restore_sessions_from_trash(self.current_codex_home, sessions)
            QtWidgets.QMessageBox.information(
                self,
                t("restore_complete_title"),
                format_restore_summary_gui(result),
            )
            self.reload_all()

        def purge_trash_selected(self) -> None:
            sessions = self.trash_panel.selected_sessions()
            if not sessions:
                QtWidgets.QMessageBox.information(self, t("no_selection_title"), t("select_trash_first"))
                return
            reply = QtWidgets.QMessageBox.warning(
                self,
                t("confirm_purge_selected_title"),
                t("confirm_purge_selected_body", count=len(sessions)),
                message_buttons.Yes | message_buttons.No,
                message_buttons.No,
            )
            if reply != message_buttons.Yes:
                return
            result = purge_trashed_sessions(self.current_codex_home, sessions)
            QtWidgets.QMessageBox.information(self, t("purge_complete_title"), format_purge_summary_gui(result))
            self.reload_all()

        def purge_trash_all(self) -> None:
            sessions = list(self.trash_sessions)
            if not sessions:
                QtWidgets.QMessageBox.information(self, t("trash_empty_title"), t("trash_empty_body"))
                return
            reply = QtWidgets.QMessageBox.warning(
                self,
                t("confirm_purge_all_title"),
                t("confirm_purge_all_body", count=len(sessions)),
                message_buttons.Yes | message_buttons.No,
                message_buttons.No,
            )
            if reply != message_buttons.Yes:
                return
            result = purge_trashed_sessions(self.current_codex_home, sessions)
            QtWidgets.QMessageBox.information(
                self,
                t("empty_trash_complete_title"),
                format_purge_summary_gui(result),
            )
            self.reload_all()

    app = QtWidgets.QApplication.instance()
    owns_app = app is None
    if app is None:
        app = QtWidgets.QApplication(sys.argv)

    icon = None
    icon_path = resolve_runtime_asset_path(APP_ICON_RELATIVE_PATH)
    if icon_path.exists():
        icon = QtGui.QIcon(str(icon_path))
        if hasattr(icon, "isNull") and not icon.isNull() and hasattr(app, "setWindowIcon"):
            app.setWindowIcon(icon)

    instance_lock = acquire_gui_instance_lock()
    if instance_lock is None:
        QtWidgets.QMessageBox.information(None, t("already_running_title"), t("already_running_body"))
        return 1

    if hasattr(app, "aboutToQuit"):
        app.aboutToQuit.connect(instance_lock.unlock)

    window = SessionManagerWindow(codex_home)
    if icon is not None and hasattr(icon, "isNull") and not icon.isNull() and hasattr(window, "setWindowIcon"):
        window.setWindowIcon(icon)
    window._instance_lock = instance_lock
    window.show()
    if owns_app:
        return app.exec() if hasattr(app, "exec") else app.exec_()
    return 0


def command_gui(args: argparse.Namespace) -> int:
    codex_home = resolve_codex_home(args.codex_home)
    try:
        return launch_gui(codex_home, language=getattr(args, "lang_override", None) or getattr(args, "requested_lang", None))
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2


def detect_requested_language(argv: list[str] | None = None) -> str | None:
    arguments = list(sys.argv[1:] if argv is None else argv)
    for index, argument in enumerate(arguments):
        if argument == "--lang" and index + 1 < len(arguments):
            return arguments[index + 1]
        if argument.startswith("--lang="):
            return argument.split("=", 1)[1]
    return None


def add_language_argument(parser: argparse.ArgumentParser, *, help_text: str, dest: str = "lang_override") -> None:
    parser.add_argument("--lang", dest=dest, metavar="LANG", help=help_text)


def add_common_filters(parser: argparse.ArgumentParser, *, default_limit: int, localize: Any) -> None:
    add_language_argument(parser, help_text=localize("lang_help"))
    parser.add_argument("--codex-home", help=localize("codex_home_help"))
    parser.add_argument("--id", action="append", help=localize("id_help"))
    parser.add_argument("--keyword", help=localize("keyword_help"))
    parser.add_argument("--project", help=localize("project_help"))
    parser.add_argument("--cwd", help=localize("cwd_help"))
    parser.add_argument("--before", help=localize("before_help"))
    parser.add_argument("--after", help=localize("after_help"))
    parser.add_argument("--missing-files", action="store_true", help=localize("missing_files_help"))
    parser.add_argument("--with-files", action="store_true", help=localize("with_files_help"))
    parser.add_argument("--limit", type=int, default=default_limit, help=localize("limit_help", default_limit=default_limit))


def build_parser(language: str | None = None) -> argparse.ArgumentParser:
    build_language = normalize_language(language or detect_requested_language(), environment_keys=("CODEX_LANG",))

    def localize(key: str, **kwargs: object) -> str:
        return format_localized_text(CLI_TRANSLATIONS, build_language, key, **kwargs)

    parser = argparse.ArgumentParser(description=localize("parser_description"))
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    add_language_argument(parser, help_text=localize("lang_help"), dest="lang")
    subparsers = parser.add_subparsers(dest="command", required=True)

    query_parser = subparsers.add_parser("query", aliases=["list"], help=localize("query_help"))
    add_common_filters(query_parser, default_limit=20, localize=localize)
    query_parser.add_argument("--json", action="store_true", help=localize("json_help"))
    query_parser.add_argument("--show-files", action="store_true", help=localize("show_files_help"))
    query_parser.set_defaults(func=command_query)

    trash_parser = subparsers.add_parser("trash", aliases=["list-trash"], help=localize("trash_help"))
    add_common_filters(trash_parser, default_limit=20, localize=localize)
    trash_parser.add_argument("--json", action="store_true", help=localize("json_help"))
    trash_parser.add_argument("--show-files", action="store_true", help=localize("trash_show_files_help"))
    trash_parser.set_defaults(func=command_trash)

    projects_parser = subparsers.add_parser("projects", help=localize("projects_help"))
    add_common_filters(projects_parser, default_limit=-1, localize=localize)
    projects_parser.add_argument("--trash", action="store_true", help=localize("projects_trash_help"))
    projects_parser.add_argument("--json", action="store_true", help=localize("json_help"))
    projects_parser.set_defaults(func=command_projects)

    export_parser = subparsers.add_parser("export", help=localize("export_help"))
    add_language_argument(export_parser, help_text=localize("lang_help"))
    export_parser.add_argument("--codex-home", help=localize("codex_home_help"))
    export_parser.add_argument("--id", required=True, help=localize("export_id_help"))
    export_parser.add_argument("--output", help=localize("export_output_help"))
    export_parser.add_argument("--trash", action="store_true", help=localize("export_trash_help"))
    export_parser.set_defaults(func=command_export)

    rename_parser = subparsers.add_parser("rename", help=localize("rename_help"))
    add_language_argument(rename_parser, help_text=localize("lang_help"))
    rename_parser.add_argument("--codex-home", help=localize("codex_home_help"))
    rename_parser.add_argument("--id", required=True, help=localize("rename_id_help"))
    rename_parser.add_argument("--name", required=True, help=localize("rename_name_help"))
    rename_parser.add_argument("--trash", action="store_true", help=localize("rename_trash_help"))
    rename_parser.set_defaults(func=command_rename)

    delete_parser = subparsers.add_parser("delete", help=localize("delete_help"))
    add_common_filters(delete_parser, default_limit=-1, localize=localize)
    delete_parser.add_argument("--dry-run", action="store_true", help=localize("dry_run_help"))
    delete_parser.add_argument("--yes", action="store_true", help=localize("yes_help"))
    delete_parser.add_argument("--permanent", action="store_true", help=localize("permanent_help"))
    delete_parser.set_defaults(func=command_delete)

    delete_all_parser = subparsers.add_parser(
        "delete-all",
        aliases=["delete_all"],
        help=localize("delete_all_help"),
    )
    add_language_argument(delete_all_parser, help_text=localize("lang_help"))
    delete_all_parser.add_argument("--codex-home", help=localize("codex_home_help"))
    delete_all_parser.add_argument("--dry-run", action="store_true", help=localize("dry_run_help"))
    delete_all_parser.add_argument("--yes", action="store_true", help=localize("yes_help"))
    delete_all_parser.add_argument("--permanent", action="store_true", help=localize("permanent_help"))
    delete_all_parser.set_defaults(func=command_delete_all)

    restore_parser = subparsers.add_parser("restore", help=localize("restore_help"))
    add_common_filters(restore_parser, default_limit=-1, localize=localize)
    restore_parser.add_argument("--all", action="store_true", help=localize("restore_all_help"))
    restore_parser.add_argument("--yes", action="store_true", help=localize("yes_help"))
    restore_parser.set_defaults(func=command_restore)

    empty_trash_parser = subparsers.add_parser("empty-trash", help=localize("empty_trash_help"))
    add_common_filters(empty_trash_parser, default_limit=-1, localize=localize)
    empty_trash_parser.add_argument("--all", action="store_true", help=localize("empty_trash_all_help"))
    empty_trash_parser.add_argument("--yes", action="store_true", help=localize("yes_help"))
    empty_trash_parser.set_defaults(func=command_empty_trash)

    gui_parser = subparsers.add_parser("gui", aliases=["qt"], help=localize("gui_help"))
    gui_parser.add_argument("--codex-home", help=localize("codex_home_help"))
    gui_parser.add_argument("--lang", dest="lang_override", help=localize("gui_lang_help"))
    gui_parser.set_defaults(func=command_gui)

    return parser


def main() -> int:
    configure_stdout()
    requested_lang = detect_requested_language()
    parser = build_parser()
    args = parser.parse_args()
    args.requested_lang = requested_lang
    args.lang = set_cli_language(getattr(args, "lang_override", None) or getattr(args, "lang", None))
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())



