from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


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
        print("没有匹配的 sessions。")
        return

    headers = ["Project", "Updated"]
    if include_deleted_at:
        headers.append("Deleted")
    headers.extend(["Files", "Size", "Source", "Session ID", "Thread"])

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
        print(f"    cwd: {session.primary_cwd}")
        if show_files:
            for path in sorted(session.rollout_paths):
                print(f"    file: {path}")


def print_sessions_json(sessions: list[SessionSummary], show_files: bool) -> None:
    payload = [session.to_dict(include_paths=show_files) for session in sessions]
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def print_projects_table(stats: list[tuple[str, int]]) -> None:
    if not stats:
        print("没有可显示的项目。")
        return

    project_width = max(len("Project"), min(max(len(project) for project, _ in stats), 72))
    count_width = max(len("Sessions"), max(len(str(count)) for _, count in stats))
    print(f"{'Project'.ljust(project_width)}  {'Sessions'.ljust(count_width)}")
    print(f"{'-' * project_width}  {'-' * count_width}")
    for project, count in stats:
        print(f"{truncate(project, project_width).ljust(project_width)}  {str(count).ljust(count_width)}")


def format_delete_summary(result: DeleteResult, *, moved_to_trash: bool) -> str:
    action = "移入回收站" if moved_to_trash else "已永久删除"
    return (
        f"{action} {result.session_count} 个 session，"
        f"{result.deleted_file_count} 个 rollout 文件，"
        f"{result.removed_index_entry_count} 条索引记录。"
    )


def format_restore_summary(result: RestoreResult) -> str:
    suffix = ""
    if result.skipped_session_ids:
        suffix = f"；跳过冲突 {len(result.skipped_session_ids)} 个：{', '.join(result.skipped_session_ids)}"
    return (
        f"已恢复 {result.restored_session_count} 个 session，"
        f"{result.restored_file_count} 个 rollout 文件，"
        f"{result.restored_index_entry_count} 条索引记录"
        f"{suffix}。"
    )


def format_purge_summary(result: PurgeResult) -> str:
    return f"已从回收站永久删除 {result.session_count} 个 session，{result.deleted_file_count} 个 rollout 文件。"


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
    print(f"将要{action}以下 sessions:")
    for session in sessions[:10]:
        print(f"- {session.session_id} | {session.thread_name or '-'}")
    if len(sessions) > 10:
        print(f"... 其余 {len(sessions) - 10} 个 session")
    answer = input("继续吗？输入 yes 确认: ").strip()
    return answer == "yes"


def command_query(args: argparse.Namespace) -> int:
    codex_home = resolve_codex_home(args.codex_home)
    sessions = filter_sessions(build_session_summaries(codex_home), args)
    if args.json:
        print_sessions_json(sessions, args.show_files)
    else:
        print_sessions_table(sessions, args.show_files)
        print(f"\n共 {len(sessions)} 个活动 session，CODEX_HOME={codex_home}")
    return 0


def command_trash(args: argparse.Namespace) -> int:
    codex_home = resolve_codex_home(args.codex_home)
    sessions = filter_sessions(build_trash_summaries(codex_home), args)
    if args.json:
        print_sessions_json(sessions, args.show_files)
    else:
        print_sessions_table(sessions, args.show_files, include_deleted_at=True)
        print(f"\n共 {len(sessions)} 个回收站 session，CODEX_HOME={codex_home}")
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
        print("没有匹配的 sessions，未执行删除。")
        return 0

    if dry_run:
        rollout_paths = {path for session in sessions for path in session.rollout_paths}
        action = "永久删除" if permanent else "移入回收站"
        print(f"dry-run: 将{action} {len(sessions)} 个 session，{len(rollout_paths)} 个 rollout 文件。")
        print_sessions_table(sessions, show_files=True)
        return 0

    action = "永久删除" if permanent else "移入回收站"
    if not yes and not confirm_sessions(action, sessions):
        print("已取消操作。")
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
        print("没有匹配的回收站 session，未执行恢复。")
        return 0
    if not args.yes and not confirm_sessions("恢复", targets):
        print("已取消操作。")
        return 1
    result = restore_sessions_from_trash(codex_home, targets)
    print(format_restore_summary(result))
    return 0


def command_empty_trash(args: argparse.Namespace) -> int:
    codex_home = resolve_codex_home(args.codex_home)
    sessions = build_trash_summaries(codex_home)
    targets = sessions if args.all else filter_sessions(sessions, args)
    if not targets:
        print("没有匹配的回收站 session，未执行清空。")
        return 0
    if not args.yes and not confirm_sessions("从回收站永久删除", targets):
        print("已取消操作。")
        return 1
    result = purge_trashed_sessions(codex_home, targets)
    print(format_purge_summary(result))
    return 0


def command_rename(args: argparse.Namespace) -> int:
    codex_home = resolve_codex_home(args.codex_home)
    changed = rename_session(codex_home, args.id, args.name, in_trash=args.trash)
    if not changed:
        scope = "回收站" if args.trash else "活动列表"
        print(f"未在{scope}找到 session: {args.id}")
        return 1
    print(f"已将 session {args.id} 重命名为: {args.name}")
    return 0


def load_qt_binding() -> tuple[str, Any, Any]:
    candidates = ("PySide6", "PyQt6", "PyQt5")
    errors: list[str] = []
    for name in candidates:
        try:
            if name == "PySide6":
                from PySide6 import QtCore, QtWidgets  # type: ignore
            elif name == "PyQt6":
                from PyQt6 import QtCore, QtWidgets  # type: ignore
            else:
                from PyQt5 import QtCore, QtWidgets  # type: ignore
            return name, QtCore, QtWidgets
        except ImportError as exc:
            errors.append(f"{name}: {exc}")
    raise RuntimeError(
        "未检测到 Qt 绑定，请先安装 PySide6、PyQt6 或 PyQt5。"
        f" 当前探测结果: {'; '.join(errors)}"
    )


def launch_gui(codex_home: Path) -> int:
    binding_name, QtCore, QtWidgets = load_qt_binding()

    resize_mode = getattr(QtWidgets.QHeaderView, "ResizeMode", QtWidgets.QHeaderView)
    selection_mode = getattr(QtWidgets.QAbstractItemView, "SelectionMode", QtWidgets.QAbstractItemView)
    selection_behavior = getattr(QtWidgets.QAbstractItemView, "SelectionBehavior", QtWidgets.QAbstractItemView)
    edit_trigger = getattr(QtWidgets.QAbstractItemView, "EditTrigger", QtWidgets.QAbstractItemView)
    message_buttons = getattr(QtWidgets.QMessageBox, "StandardButton", QtWidgets.QMessageBox)
    sort_order = getattr(QtCore.Qt, "SortOrder", QtCore.Qt)

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
        def __init__(self, *, include_deleted_at: bool, button_specs: list[tuple[str, str]], title: str) -> None:
            super().__init__()
            self.include_deleted_at = include_deleted_at
            self.title = title
            self.all_sessions: list[SessionSummary] = []
            self.visible_sessions: list[SessionSummary] = []
            self.session_by_id: dict[str, SessionSummary] = {}
            self.on_state_changed: Any = None
            self.on_thread_double_clicked: Any = None

            layout = QtWidgets.QVBoxLayout(self)

            filter_layout = QtWidgets.QHBoxLayout()
            filter_layout.addWidget(QtWidgets.QLabel("项目"))
            self.project_combo = QtWidgets.QComboBox()
            self.project_combo.addItem("全部项目", "")
            filter_layout.addWidget(self.project_combo)
            filter_layout.addWidget(QtWidgets.QLabel("搜索"))
            self.filter_edit = QtWidgets.QLineEdit()
            self.filter_edit.setPlaceholderText("按项目、session id、标题、cwd、source 过滤")
            filter_layout.addWidget(self.filter_edit, 1)
            layout.addLayout(filter_layout)

            headers = ["Project", "Updated"]
            if self.include_deleted_at:
                headers.append("Deleted")
            headers.extend(["Files", "Size", "Source", "Session ID", "Thread", "CWD"])
            self.session_id_column = headers.index("Session ID")
            self.thread_column = headers.index("Thread")

            self.table = QtWidgets.QTableWidget(0, len(headers))
            self.table.setHorizontalHeaderLabels(headers)
            self.table.setSelectionBehavior(selection_behavior.SelectRows)
            self.table.setSelectionMode(selection_mode.ExtendedSelection)
            self.table.setEditTriggers(edit_trigger.NoEditTriggers)
            self.table.setAlternatingRowColors(True)
            self.table.setSortingEnabled(True)
            self.table.verticalHeader().setVisible(False)
            header = self.table.horizontalHeader()
            for column in range(len(headers)):
                mode = resize_mode.ResizeToContents if column < len(headers) - 2 else resize_mode.Stretch
                header.setSectionResizeMode(column, mode)
            layout.addWidget(self.table, 1)

            button_layout = QtWidgets.QHBoxLayout()
            self.buttons: dict[str, Any] = {}
            for key, label in button_specs:
                button = QtWidgets.QPushButton(label)
                self.buttons[key] = button
                button_layout.addWidget(button)
            button_layout.addStretch(1)
            layout.addLayout(button_layout)

            self.project_combo.currentIndexChanged.connect(self.apply_filter)
            self.filter_edit.textChanged.connect(self.apply_filter)
            self.table.itemSelectionChanged.connect(self._notify_state_changed)
            self.table.itemDoubleClicked.connect(self._handle_item_double_clicked)

            if "select_all" in self.buttons:
                self.buttons["select_all"].clicked.connect(self.select_all_rows)
            if "clear_selection" in self.buttons:
                self.buttons["clear_selection"].clicked.connect(self.clear_selection)

        def _notify_state_changed(self) -> None:
            if callable(self.on_state_changed):
                self.on_state_changed()

        def _handle_item_double_clicked(self, item: Any) -> None:
            if item is None or item.column() != self.thread_column:
                return
            session = self.session_for_row(item.row())
            if session is None:
                return
            if callable(self.on_thread_double_clicked):
                self.on_thread_double_clicked(session)

        def set_sessions(self, sessions: list[SessionSummary]) -> None:
            self.all_sessions = list(sessions)
            self.session_by_id = {session.session_id: session for session in sessions}
            self.refresh_project_options()
            self.apply_filter()

        def refresh_project_options(self) -> None:
            current_value = self.project_combo.currentData()
            projects = sorted({session.primary_project for session in self.all_sessions})
            self.project_combo.blockSignals(True)
            self.project_combo.clear()
            self.project_combo.addItem("全部项目", "")
            for project in projects:
                label = "(未知项目)" if project == "-" else project
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
                values = [session.primary_project, format_timestamp(session.updated_at)]
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

            self.setWindowTitle("Codex Session Manager")
            self.resize(1420, 860)

            root_layout = QtWidgets.QVBoxLayout(self)

            path_layout = QtWidgets.QHBoxLayout()
            path_layout.addWidget(QtWidgets.QLabel("CODEX_HOME"))
            self.codex_home_edit = QtWidgets.QLineEdit(str(initial_codex_home))
            path_layout.addWidget(self.codex_home_edit, 1)
            self.browse_button = QtWidgets.QPushButton("浏览")
            self.refresh_button = QtWidgets.QPushButton("刷新")
            path_layout.addWidget(self.browse_button)
            path_layout.addWidget(self.refresh_button)
            root_layout.addLayout(path_layout)

            self.info_label = QtWidgets.QLabel(f"Qt: {binding_name}")
            root_layout.addWidget(self.info_label)

            self.tabs = QtWidgets.QTabWidget()
            self.active_panel = SessionPanel(
                include_deleted_at=False,
                title="活动 sessions",
                button_specs=[
                    ("select_all", "全选"),
                    ("clear_selection", "清空选择"),
                    ("rename", "重命名"),
                    ("delete", "删除到回收站"),
                ],
            )
            self.trash_panel = SessionPanel(
                include_deleted_at=True,
                title="回收站",
                button_specs=[
                    ("select_all", "全选"),
                    ("clear_selection", "清空选择"),
                    ("rename", "重命名"),
                    ("restore", "恢复所选"),
                    ("purge_selected", "彻底删除所选"),
                    ("purge_all", "清空回收站"),
                ],
            )
            self.tabs.addTab(self.active_panel, "活动 sessions")
            self.tabs.addTab(self.trash_panel, "回收站")
            root_layout.addWidget(self.tabs, 1)

            self.status_label = QtWidgets.QLabel("就绪")
            root_layout.addWidget(self.status_label)

            self.browse_button.clicked.connect(self.choose_codex_home)
            self.refresh_button.clicked.connect(self.reload_all)
            self.tabs.currentChanged.connect(self.update_status)
            self.active_panel.on_state_changed = self.update_status
            self.trash_panel.on_state_changed = self.update_status
            self.active_panel.on_thread_double_clicked = self.rename_active_session
            self.trash_panel.on_thread_double_clicked = self.rename_trash_session

            self.active_panel.buttons["rename"].clicked.connect(self.rename_active_selected)
            self.active_panel.buttons["delete"].clicked.connect(self.delete_active_selected)
            self.trash_panel.buttons["rename"].clicked.connect(self.rename_trash_selected)
            self.trash_panel.buttons["restore"].clicked.connect(self.restore_trash_selected)
            self.trash_panel.buttons["purge_selected"].clicked.connect(self.purge_trash_selected)
            self.trash_panel.buttons["purge_all"].clicked.connect(self.purge_trash_all)

            self.reload_all()

        def resolve_current_codex_home(self) -> Path:
            return resolve_codex_home(self.codex_home_edit.text().strip() or None)

        def choose_codex_home(self) -> None:
            selected = QtWidgets.QFileDialog.getExistingDirectory(self, "选择 CODEX_HOME", self.codex_home_edit.text())
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
                QtWidgets.QMessageBox.critical(self, "加载失败", str(exc))
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
                f"CODEX_HOME: {self.current_codex_home} | 活动 {len(self.active_sessions)} | 回收站 {len(self.trash_sessions)} | 当前: {title} 显示 {visible_count} | 已选 {selected_count}"
            )

        def prompt_new_name(self, current_name: str) -> str | None:
            text, accepted = QtWidgets.QInputDialog.getText(self, "重命名 session", "新的名称：", text=current_name)
            if not accepted:
                return None
            value = text.strip()
            return value or None

        def rename_one_session(self, session: SessionSummary, *, in_trash: bool) -> None:
            new_name = self.prompt_new_name(session.thread_name or "")
            if not new_name:
                return
            changed = rename_session(self.current_codex_home, session.session_id, new_name, in_trash=in_trash)
            if not changed:
                QtWidgets.QMessageBox.warning(self, "重命名失败", f"未找到 session: {session.session_id}")
                return
            self.reload_all()

        def rename_selected(self, *, in_trash: bool) -> None:
            panel = self.trash_panel if in_trash else self.active_panel
            sessions = panel.selected_sessions()
            if len(sessions) != 1:
                QtWidgets.QMessageBox.information(self, "请选择一条", "重命名只支持单选 session。")
                return
            self.rename_one_session(sessions[0], in_trash=in_trash)

        def rename_active_selected(self) -> None:
            self.rename_selected(in_trash=False)

        def rename_trash_selected(self) -> None:
            self.rename_selected(in_trash=True)

        def rename_active_session(self, session: SessionSummary) -> None:
            self.rename_one_session(session, in_trash=False)

        def rename_trash_session(self, session: SessionSummary) -> None:
            self.rename_one_session(session, in_trash=True)

        def delete_active_selected(self) -> None:
            sessions = self.active_panel.selected_sessions()
            if not sessions:
                QtWidgets.QMessageBox.information(self, "未选择", "请先选择一个或多个活动 session。")
                return
            preview = [f"- {session.session_id} | {session.thread_name or '-'}" for session in sessions[:8]]
            if len(sessions) > 8:
                preview.append(f"... 其余 {len(sessions) - 8} 个 session")
            reply = QtWidgets.QMessageBox.question(
                self,
                "确认删除",
                "将以下 session 移入回收站：\n\n" + "\n".join(preview),
                message_buttons.Yes | message_buttons.No,
                message_buttons.No,
            )
            if reply != message_buttons.Yes:
                return
            result = move_sessions_to_trash(self.current_codex_home, sessions)
            QtWidgets.QMessageBox.information(self, "删除完成", format_delete_summary(result, moved_to_trash=True))
            self.reload_all()

        def restore_trash_selected(self) -> None:
            sessions = self.trash_panel.selected_sessions()
            if not sessions:
                QtWidgets.QMessageBox.information(self, "未选择", "请先选择一个或多个回收站 session。")
                return
            reply = QtWidgets.QMessageBox.question(
                self,
                "确认恢复",
                f"确认恢复所选 {len(sessions)} 个 session 吗？",
                message_buttons.Yes | message_buttons.No,
                message_buttons.Yes,
            )
            if reply != message_buttons.Yes:
                return
            result = restore_sessions_from_trash(self.current_codex_home, sessions)
            QtWidgets.QMessageBox.information(self, "恢复完成", format_restore_summary(result))
            self.reload_all()

        def purge_trash_selected(self) -> None:
            sessions = self.trash_panel.selected_sessions()
            if not sessions:
                QtWidgets.QMessageBox.information(self, "未选择", "请先选择一个或多个回收站 session。")
                return
            reply = QtWidgets.QMessageBox.warning(
                self,
                "确认永久删除",
                f"确认从回收站永久删除所选 {len(sessions)} 个 session 吗？该操作不可恢复。",
                message_buttons.Yes | message_buttons.No,
                message_buttons.No,
            )
            if reply != message_buttons.Yes:
                return
            result = purge_trashed_sessions(self.current_codex_home, sessions)
            QtWidgets.QMessageBox.information(self, "删除完成", format_purge_summary(result))
            self.reload_all()

        def purge_trash_all(self) -> None:
            sessions = list(self.trash_sessions)
            if not sessions:
                QtWidgets.QMessageBox.information(self, "回收站为空", "当前没有可清空的回收站 session。")
                return
            reply = QtWidgets.QMessageBox.warning(
                self,
                "清空回收站",
                f"确认清空回收站中的全部 {len(sessions)} 个 session 吗？该操作不可恢复。",
                message_buttons.Yes | message_buttons.No,
                message_buttons.No,
            )
            if reply != message_buttons.Yes:
                return
            result = purge_trashed_sessions(self.current_codex_home, sessions)
            QtWidgets.QMessageBox.information(self, "清空完成", format_purge_summary(result))
            self.reload_all()

    app = QtWidgets.QApplication.instance()
    owns_app = app is None
    if app is None:
        app = QtWidgets.QApplication(sys.argv)

    instance_lock = acquire_gui_instance_lock()
    if instance_lock is None:
        QtWidgets.QMessageBox.information(None, "已在运行", "`manage_codex_sessions` GUI 已在运行，只允许一个实例。")
        return 1

    if hasattr(app, "aboutToQuit"):
        app.aboutToQuit.connect(instance_lock.unlock)

    window = SessionManagerWindow(codex_home)
    window._instance_lock = instance_lock
    window.show()
    if owns_app:
        return app.exec() if hasattr(app, "exec") else app.exec_()
    return 0


def command_gui(args: argparse.Namespace) -> int:
    codex_home = resolve_codex_home(args.codex_home)
    try:
        return launch_gui(codex_home)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2


def add_common_filters(parser: argparse.ArgumentParser, *, default_limit: int) -> None:
    parser.add_argument("--codex-home", help="Codex 数据目录，默认读取 CODEX_HOME 或 ~/.codex。")
    parser.add_argument("--id", action="append", help="按 session id 精确匹配，可重复传入。")
    parser.add_argument("--keyword", help="按 session id、thread name、cwd、project 模糊匹配。")
    parser.add_argument("--project", help="按项目路径模糊匹配。")
    parser.add_argument("--cwd", help="按 cwd 模糊匹配。")
    parser.add_argument("--before", help="仅匹配 updated_at 早于该时间的 session，例如 2026-10-01T00:00:00Z。")
    parser.add_argument("--after", help="仅匹配 updated_at 晚于该时间的 session，例如 2026-10-01T00:00:00Z。")
    parser.add_argument("--missing-files", action="store_true", help="仅匹配没有 rollout 文件的 session。")
    parser.add_argument("--with-files", action="store_true", help="仅匹配存在 rollout 文件的 session。")
    parser.add_argument("--limit", type=int, default=default_limit, help=f"返回的最大 session 数，默认 {default_limit}；传 -1 表示不限制。")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage local Codex sessions, recycle bin, rename, and Qt UI.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    query_parser = subparsers.add_parser("query", aliases=["list"], help="查询活动 sessions。")
    add_common_filters(query_parser, default_limit=20)
    query_parser.add_argument("--json", action="store_true", help="输出 JSON。")
    query_parser.add_argument("--show-files", action="store_true", help="输出每个 session 对应的 rollout 文件路径。")
    query_parser.set_defaults(func=command_query)

    trash_parser = subparsers.add_parser("trash", aliases=["list-trash"], help="查询回收站 sessions。")
    add_common_filters(trash_parser, default_limit=20)
    trash_parser.add_argument("--json", action="store_true", help="输出 JSON。")
    trash_parser.add_argument("--show-files", action="store_true", help="输出每个 session 对应的回收站文件路径。")
    trash_parser.set_defaults(func=command_trash)

    projects_parser = subparsers.add_parser("projects", help="按项目统计 sessions。")
    add_common_filters(projects_parser, default_limit=-1)
    projects_parser.add_argument("--trash", action="store_true", help="统计回收站中的 sessions。")
    projects_parser.add_argument("--json", action="store_true", help="输出 JSON。")
    projects_parser.set_defaults(func=command_projects)

    rename_parser = subparsers.add_parser("rename", help="重命名 session。")
    rename_parser.add_argument("--codex-home", help="Codex 数据目录，默认读取 CODEX_HOME 或 ~/.codex。")
    rename_parser.add_argument("--id", required=True, help="目标 session id。")
    rename_parser.add_argument("--name", required=True, help="新的 session 名称。")
    rename_parser.add_argument("--trash", action="store_true", help="重命名回收站中的 session。")
    rename_parser.set_defaults(func=command_rename)

    delete_parser = subparsers.add_parser("delete", help="删除活动 session，默认移入回收站。")
    add_common_filters(delete_parser, default_limit=-1)
    delete_parser.add_argument("--dry-run", action="store_true", help="仅预览将删除的 session 和文件。")
    delete_parser.add_argument("--yes", action="store_true", help="跳过交互确认。")
    delete_parser.add_argument("--permanent", action="store_true", help="直接永久删除，不经过回收站。")
    delete_parser.set_defaults(func=command_delete)

    delete_all_parser = subparsers.add_parser(
        "delete-all",
        aliases=["delete_all", "delte_all"],
        help="删除全部活动 session，默认移入回收站。",
    )
    delete_all_parser.add_argument("--codex-home", help="Codex 数据目录，默认读取 CODEX_HOME 或 ~/.codex。")
    delete_all_parser.add_argument("--dry-run", action="store_true", help="仅预览将删除的 session 和文件。")
    delete_all_parser.add_argument("--yes", action="store_true", help="跳过交互确认。")
    delete_all_parser.add_argument("--permanent", action="store_true", help="直接永久删除，不经过回收站。")
    delete_all_parser.set_defaults(func=command_delete_all)

    restore_parser = subparsers.add_parser("restore", help="从回收站恢复 session。")
    add_common_filters(restore_parser, default_limit=-1)
    restore_parser.add_argument("--all", action="store_true", help="恢复回收站全部 session。")
    restore_parser.add_argument("--yes", action="store_true", help="跳过交互确认。")
    restore_parser.set_defaults(func=command_restore)

    empty_trash_parser = subparsers.add_parser("empty-trash", help="从回收站永久删除 session。")
    add_common_filters(empty_trash_parser, default_limit=-1)
    empty_trash_parser.add_argument("--all", action="store_true", help="清空回收站全部 session。")
    empty_trash_parser.add_argument("--yes", action="store_true", help="跳过交互确认。")
    empty_trash_parser.set_defaults(func=command_empty_trash)

    gui_parser = subparsers.add_parser("gui", aliases=["qt"], help="启动 Qt 图形界面管理 sessions。")
    gui_parser.add_argument("--codex-home", help="Codex 数据目录，默认读取 CODEX_HOME 或 ~/.codex。")
    gui_parser.set_defaults(func=command_gui)

    return parser


def main() -> int:
    configure_stdout()
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())



