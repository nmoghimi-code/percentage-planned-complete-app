from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable


DATE_FORMATS = (
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d",
    "%d-%b-%y %H:%M",
    "%d-%b-%y",
    "%m/%d/%Y %H:%M",
    "%m/%d/%Y",
)

DATA_DATE_FIELDS = (
    "last_recalc_date",
    "status_date",
    "data_date",
    "update_date",
)

PLANNED_START_FIELDS = (
    "early_start_date",
    "target_start_date",
)

PLANNED_FINISH_FIELDS = (
    "early_end_date",
    "target_end_date",
)

ACTUAL_START_FIELDS = (
    "act_start_date",
    "actual_start_date",
)

ACTUAL_FINISH_FIELDS = (
    "act_end_date",
    "actual_end_date",
)

ACTIVITY_ID_FIELDS = (
    "task_code",
    "activity_id",
)


@dataclass(frozen=True)
class ProjectInfo:
    project_id: str
    name: str
    data_date: datetime


@dataclass(frozen=True)
class WBSNode:
    wbs_id: str
    project_id: str
    parent_wbs_id: str
    name: str
    short_name: str


@dataclass(frozen=True)
class Activity:
    task_id: str
    project_id: str
    wbs_id: str
    activity_id: str
    name: str
    activity_type: str
    remaining_start: datetime | None
    remaining_finish: datetime | None
    planned_start: datetime | None
    planned_finish: datetime | None
    actual_start: datetime | None
    actual_finish: datetime | None


@dataclass(frozen=True)
class XerSchedule:
    source_path: Path
    project: ProjectInfo
    wbs_nodes: dict[str, WBSNode]
    activities: list[Activity]

    def branch_activity_ids(self, branch_name: str) -> set[str]:
        matching_roots = {
            node.wbs_id
            for node in self.wbs_nodes.values()
            if node.project_id == self.project.project_id
            and _node_matches_branch(node, branch_name)
        }
        if not matching_roots:
            return set()

        descendants = set(matching_roots)
        changed = True
        while changed:
            changed = False
            for node in self.wbs_nodes.values():
                if node.project_id != self.project.project_id:
                    continue
                if node.parent_wbs_id and node.parent_wbs_id in descendants and node.wbs_id not in descendants:
                    descendants.add(node.wbs_id)
                    changed = True
        return descendants

    def activities_in_branch(self, branch_name: str) -> list[Activity]:
        branch_wbs_ids = self.branch_activity_ids(branch_name)
        return [activity for activity in self.activities if activity.wbs_id in branch_wbs_ids]


def parse_xer_file(path: str | Path) -> XerSchedule:
    source_path = Path(path)
    tables = _parse_tables(source_path)

    projects = tables.get("PROJECT", [])
    if not projects:
        raise ValueError(f"No PROJECT table rows found in {source_path.name}")

    project_row = _select_project_row(projects)
    project_id = project_row.get("proj_id", "")
    project_name = project_row.get("proj_short_name") or project_row.get("proj_name") or source_path.stem

    data_date = None
    for field_name in DATA_DATE_FIELDS:
        data_date = parse_xer_datetime(project_row.get(field_name))
        if data_date:
            break
    if data_date is None:
        raise ValueError(
            f"Unable to determine the project data date from the PROJECT table in {source_path.name}"
        )

    project = ProjectInfo(project_id=project_id, name=project_name, data_date=data_date)

    wbs_nodes: dict[str, WBSNode] = {}
    for row in tables.get("PROJWBS", []):
        if row.get("proj_id") != project.project_id:
            continue
        node = WBSNode(
            wbs_id=row.get("wbs_id", ""),
            project_id=row.get("proj_id", ""),
            parent_wbs_id=row.get("parent_wbs_id", ""),
            name=row.get("wbs_name", ""),
            short_name=row.get("wbs_short_name", ""),
        )
        wbs_nodes[node.wbs_id] = node

    activities: list[Activity] = []
    for row in tables.get("TASK", []):
        if row.get("proj_id") != project.project_id:
            continue
        activities.append(
            Activity(
                task_id=row.get("task_id", ""),
                project_id=row.get("proj_id", ""),
                wbs_id=row.get("wbs_id", ""),
                activity_id=_first_value(row, ACTIVITY_ID_FIELDS),
                name=row.get("task_name", ""),
                activity_type=row.get("task_type", ""),
                remaining_start=parse_xer_datetime(row.get("restart_date")),
                remaining_finish=parse_xer_datetime(row.get("reend_date")),
                planned_start=_parse_first_datetime(row, PLANNED_START_FIELDS),
                planned_finish=_parse_first_datetime(row, PLANNED_FINISH_FIELDS),
                actual_start=_parse_first_datetime(row, ACTUAL_START_FIELDS),
                actual_finish=_parse_first_datetime(row, ACTUAL_FINISH_FIELDS),
            )
        )

    return XerSchedule(
        source_path=source_path,
        project=project,
        wbs_nodes=wbs_nodes,
        activities=activities,
    )


def parse_xer_datetime(raw_value: str | None) -> datetime | None:
    if raw_value is None:
        return None

    value = raw_value.strip()
    if not value:
        return None

    try:
        return datetime.fromisoformat(value)
    except ValueError:
        pass

    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def normalize_text(value: str | None) -> str:
    return (value or "").strip().casefold()


def compact_text(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", "", normalize_text(value))


def tokenize_text(value: str | None) -> tuple[str, ...]:
    return tuple(token for token in re.split(r"[^a-z0-9]+", normalize_text(value)) if token)


def is_task_dependent_type(value: str | None) -> bool:
    normalized = normalize_text(value)
    compact = compact_text(value)
    tokens = set(tokenize_text(value))

    if not normalized:
        return False

    if compact in {"taskdependent", "taskdep", "tttask"}:
        return True

    if "milestone" in tokens or "level" in tokens or "resource" in tokens or "wbs" in tokens:
        return False

    return "task" in tokens and any(token.startswith("dep") for token in tokens)


def _parse_tables(source_path: Path) -> dict[str, list[dict[str, str]]]:
    tables: dict[str, list[dict[str, str]]] = {}
    current_table_name: str | None = None
    current_fields: list[str] = []

    with source_path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
        reader = csv.reader(handle, delimiter="\t")
        for parts in reader:
            if not parts:
                continue

            record_type = parts[0]
            if record_type == "%T":
                current_table_name = parts[1] if len(parts) > 1 else None
                current_fields = []
                if current_table_name:
                    tables.setdefault(current_table_name, [])
            elif record_type == "%F":
                current_fields = parts[1:]
            elif record_type == "%R" and current_table_name and current_fields:
                row_values = parts[1:]
                row = {
                    field_name: row_values[index] if index < len(row_values) else ""
                    for index, field_name in enumerate(current_fields)
                }
                tables[current_table_name].append(row)
    return tables


def _select_project_row(project_rows: Iterable[dict[str, str]]) -> dict[str, str]:
    rows = list(project_rows)
    for field_name in DATA_DATE_FIELDS:
        for row in rows:
            if parse_xer_datetime(row.get(field_name)):
                return row
    return rows[0]


def _parse_first_datetime(row: dict[str, str], field_names: Iterable[str]) -> datetime | None:
    for field_name in field_names:
        parsed = parse_xer_datetime(row.get(field_name))
        if parsed:
            return parsed
    return None


def _first_value(row: dict[str, str], field_names: Iterable[str]) -> str:
    for field_name in field_names:
        value = row.get(field_name, "")
        if value:
            return value
    return ""


def _node_matches_branch(node: WBSNode, branch_name: str) -> bool:
    return _text_matches_branch(node.name, branch_name) or _text_matches_branch(node.short_name, branch_name)


def _text_matches_branch(value: str | None, branch_name: str) -> bool:
    tokens = set(tokenize_text(value))
    compact = compact_text(value)
    branch_key = compact_text(branch_name)

    if not compact:
        return False

    if branch_key == "preconstruction":
        return (
            "preconstruction" in compact
            or "precon" in compact
            or ("pre" in tokens and any(token.startswith(("construct", "const")) for token in tokens))
        )

    if branch_key == "construction":
        return (
            (
                "construction" in compact
                or any(token.startswith(("construct", "const")) for token in tokens)
                or compact == "con"
            )
            and not _text_matches_branch(value, "Preconstruction")
        )

    return branch_key in compact
