from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime

from .xer_parser import Activity, XerSchedule, is_task_dependent_type, normalize_text


BRANCHES = ("Preconstruction", "Construction", "Integrated Phased Planning")


@dataclass(frozen=True)
class ActivityCheck:
    project_name: str
    branch: str
    activity_id: str
    activity_name: str
    planned_date: datetime
    actual_date: datetime | None
    actualized: bool
    match_method: str


@dataclass(frozen=True)
class ActualizedActivityDetail:
    project_name: str
    branch: str
    activity_id: str
    activity_name: str
    planned_date: datetime | None
    actual_date: datetime
    match_method: str


@dataclass(frozen=True)
class SummaryRow:
    branch: str
    planned_count: int
    actualized_planned_count: int
    total_actualized_count: int
    unplanned_actualized_count: int
    planned_completion_percentage: float
    total_actualized_over_planned_percentage: float
    planned_share_of_actualized_percentage: float


@dataclass(frozen=True)
class AnalysisResult:
    previous_data_date: datetime
    current_data_date: datetime
    starts_summary: list[SummaryRow]
    finishes_summary: list[SummaryRow]
    start_details: list[ActivityCheck]
    finish_details: list[ActivityCheck]
    actualized_planned_start_details: list[ActualizedActivityDetail]
    actualized_unplanned_start_details: list[ActualizedActivityDetail]
    actualized_planned_finish_details: list[ActualizedActivityDetail]
    actualized_unplanned_finish_details: list[ActualizedActivityDetail]
    missing_branches: list[str]


@dataclass(frozen=True)
class ProjectAnalysis:
    project_name: str
    display_name: str
    previous_project_id: str
    current_project_id: str
    result: AnalysisResult


@dataclass(frozen=True)
class MultiProjectAnalysisResult:
    project_results: list[ProjectAnalysis]
    unmatched_previous_projects: list[str]
    unmatched_current_projects: list[str]


def analyze_schedules(previous_schedule: XerSchedule, current_schedule: XerSchedule) -> AnalysisResult:
    previous_data_date = previous_schedule.project.data_date
    current_data_date = current_schedule.project.data_date
    if current_data_date < previous_data_date:
        raise ValueError("The current schedule data date is earlier than the previous schedule data date.")

    project_name = previous_schedule.project.name
    starts_summary: list[SummaryRow] = []
    finishes_summary: list[SummaryRow] = []
    start_details: list[ActivityCheck] = []
    finish_details: list[ActivityCheck] = []
    actualized_planned_start_details: list[ActualizedActivityDetail] = []
    actualized_unplanned_start_details: list[ActualizedActivityDetail] = []
    actualized_planned_finish_details: list[ActualizedActivityDetail] = []
    actualized_unplanned_finish_details: list[ActualizedActivityDetail] = []
    missing_branches: list[str] = []

    for branch in BRANCHES:
        previous_branch_activities = _filter_task_dependent(previous_schedule.activities_in_branch(branch))
        current_branch_activities = _filter_task_dependent(current_schedule.activities_in_branch(branch))
        if not previous_branch_activities or not current_branch_activities:
            missing_branches.append(branch)

        current_index = _build_activity_index(current_branch_activities)
        previous_index = _build_activity_index(previous_branch_activities)

        branch_start_checks = _analyze_activity_dates(
            project_name=project_name,
            branch=branch,
            previous_activities=previous_branch_activities,
            current_index=current_index,
            previous_data_date=previous_data_date,
            current_data_date=current_data_date,
            date_type="start",
        )
        branch_finish_checks = _analyze_activity_dates(
            project_name=project_name,
            branch=branch,
            previous_activities=previous_branch_activities,
            current_index=current_index,
            previous_data_date=previous_data_date,
            current_data_date=current_data_date,
            date_type="finish",
        )
        branch_start_actualized = _find_current_actualized_activities(
            project_name=project_name,
            branch=branch,
            current_activities=current_branch_activities,
            previous_index=previous_index,
            previous_data_date=previous_data_date,
            current_data_date=current_data_date,
            date_type="start",
        )
        branch_finish_actualized = _find_current_actualized_activities(
            project_name=project_name,
            branch=branch,
            current_activities=current_branch_activities,
            previous_index=previous_index,
            previous_data_date=previous_data_date,
            current_data_date=current_data_date,
            date_type="finish",
        )

        starts_summary.append(_build_summary_row(branch, branch_start_checks, branch_start_actualized))
        finishes_summary.append(_build_summary_row(branch, branch_finish_checks, branch_finish_actualized))
        start_details.extend(branch_start_checks)
        finish_details.extend(branch_finish_checks)
        actualized_planned_start_details.extend(_to_actualized_details(branch_start_actualized, planned_in_window=True))
        actualized_unplanned_start_details.extend(_to_actualized_details(branch_start_actualized, planned_in_window=False))
        actualized_planned_finish_details.extend(_to_actualized_details(branch_finish_actualized, planned_in_window=True))
        actualized_unplanned_finish_details.extend(_to_actualized_details(branch_finish_actualized, planned_in_window=False))

    return AnalysisResult(
        previous_data_date=previous_data_date,
        current_data_date=current_data_date,
        starts_summary=starts_summary,
        finishes_summary=finishes_summary,
        start_details=sorted(start_details, key=lambda item: (normalize_text(item.project_name), item.branch, item.planned_date, item.activity_id)),
        finish_details=sorted(finish_details, key=lambda item: (normalize_text(item.project_name), item.branch, item.planned_date, item.activity_id)),
        actualized_planned_start_details=sorted(
            actualized_planned_start_details,
            key=lambda item: (normalize_text(item.project_name), item.branch, item.actual_date, item.activity_id),
        ),
        actualized_unplanned_start_details=sorted(
            actualized_unplanned_start_details,
            key=lambda item: (normalize_text(item.project_name), item.branch, item.actual_date, item.activity_id),
        ),
        actualized_planned_finish_details=sorted(
            actualized_planned_finish_details,
            key=lambda item: (normalize_text(item.project_name), item.branch, item.actual_date, item.activity_id),
        ),
        actualized_unplanned_finish_details=sorted(
            actualized_unplanned_finish_details,
            key=lambda item: (normalize_text(item.project_name), item.branch, item.actual_date, item.activity_id),
        ),
        missing_branches=sorted(set(missing_branches)),
    )


def analyze_schedule_collections(
    previous_schedules: list[XerSchedule],
    current_schedules: list[XerSchedule],
) -> MultiProjectAnalysisResult:
    current_by_key = _project_key_map(current_schedules)
    project_results: list[ProjectAnalysis] = []
    unmatched_previous: list[str] = []
    matched_current_keys: set[str] = set()

    for previous_schedule in previous_schedules:
        match_key = _project_match_key(previous_schedule)
        current_schedule = current_by_key.get(match_key)
        if current_schedule is None:
            unmatched_previous.append(previous_schedule.project.name)
            continue

        matched_current_keys.add(match_key)
        project_results.append(
            ProjectAnalysis(
                project_name=previous_schedule.project.name,
                display_name=_display_project_name(previous_schedule.project.name),
                previous_project_id=previous_schedule.project.project_id,
                current_project_id=current_schedule.project.project_id,
                result=analyze_schedules(previous_schedule, current_schedule),
            )
        )

    unmatched_current = [
        schedule.project.name
        for key, schedule in current_by_key.items()
        if key not in matched_current_keys
    ]

    return MultiProjectAnalysisResult(
        project_results=sorted(project_results, key=lambda item: normalize_text(item.project_name)),
        unmatched_previous_projects=sorted(unmatched_previous, key=normalize_text),
        unmatched_current_projects=sorted(unmatched_current, key=normalize_text),
    )


def _analyze_activity_dates(
    *,
    project_name: str,
    branch: str,
    previous_activities: list[Activity],
    current_index: dict[str, dict[str, Activity]],
    previous_data_date: datetime,
    current_data_date: datetime,
    date_type: str,
) -> list[ActivityCheck]:
    checks: list[ActivityCheck] = []
    for activity in previous_activities:
        planned_date = _previous_horizon_date(activity, date_type)
        if planned_date is None:
            continue
        if not (previous_data_date <= planned_date <= current_data_date):
            continue

        current_activity, match_method = _match_activity(activity, current_index)
        actual_date = None
        if current_activity:
            actual_date = current_activity.actual_start if date_type == "start" else current_activity.actual_finish

        checks.append(
            ActivityCheck(
                project_name=project_name,
                branch=branch,
                activity_id=activity.activity_id,
                activity_name=activity.name,
                planned_date=planned_date,
                actual_date=actual_date,
                actualized=actual_date is not None and _is_within_tracking_window(actual_date, previous_data_date, current_data_date),
                match_method=match_method,
            )
        )
    return checks


def _find_current_actualized_activities(
    *,
    project_name: str,
    branch: str,
    current_activities: list[Activity],
    previous_index: dict[str, dict[str, Activity]],
    previous_data_date: datetime,
    current_data_date: datetime,
    date_type: str,
) -> list[ActivityCheck]:
    checks: list[ActivityCheck] = []
    for activity in current_activities:
        actual_date = activity.actual_start if date_type == "start" else activity.actual_finish
        if actual_date is None or not _is_within_tracking_window(actual_date, previous_data_date, current_data_date):
            continue

        previous_activity, match_method = _match_activity(activity, previous_index)
        planned_date = None
        if previous_activity:
            planned_date = _previous_horizon_date(previous_activity, date_type)

        checks.append(
            ActivityCheck(
                project_name=project_name,
                branch=branch,
                activity_id=activity.activity_id,
                activity_name=activity.name,
                planned_date=planned_date or actual_date,
                actual_date=actual_date,
                actualized=planned_date is not None and previous_data_date <= planned_date <= current_data_date,
                match_method=match_method,
            )
        )
    return checks


def _to_actualized_details(
    checks: list[ActivityCheck],
    *,
    planned_in_window: bool,
) -> list[ActualizedActivityDetail]:
    details: list[ActualizedActivityDetail] = []
    for check in checks:
        if check.actualized != planned_in_window or check.actual_date is None:
            continue
        details.append(
            ActualizedActivityDetail(
                project_name=check.project_name,
                branch=check.branch,
                activity_id=check.activity_id,
                activity_name=check.activity_name,
                planned_date=check.planned_date if planned_in_window else None,
                actual_date=check.actual_date,
                match_method=check.match_method,
            )
        )
    return details


def _build_activity_index(activities: list[Activity]) -> dict[str, dict[str, Activity]]:
    by_id: dict[str, Activity] = {}
    by_name: dict[str, Activity] = {}
    for activity in activities:
        activity_id_key = normalize_text(activity.activity_id)
        if activity_id_key and activity_id_key not in by_id:
            by_id[activity_id_key] = activity
        activity_name_key = normalize_text(activity.name)
        if activity_name_key and activity_name_key not in by_name:
            by_name[activity_name_key] = activity
    return {"by_id": by_id, "by_name": by_name}


def _match_activity(activity: Activity, current_index: dict[str, dict[str, Activity]]) -> tuple[Activity | None, str]:
    activity_id_key = normalize_text(activity.activity_id)
    if activity_id_key:
        matched = current_index["by_id"].get(activity_id_key)
        if matched:
            return matched, "Activity ID"

    name_key = normalize_text(activity.name)
    if name_key:
        matched = current_index["by_name"].get(name_key)
        if matched:
            return matched, "Activity Name"

    return None, "Not found"


def _build_summary_row(
    branch: str,
    planned_checks: list[ActivityCheck],
    actualized_checks: list[ActivityCheck],
) -> SummaryRow:
    planned_count = len(planned_checks)
    actualized_planned_count = sum(1 for check in planned_checks if check.actualized)
    total_actualized_count = len(actualized_checks)
    unplanned_actualized_count = sum(1 for check in actualized_checks if not check.actualized)
    planned_completion_percentage = (actualized_planned_count / planned_count * 100.0) if planned_count else 0.0
    total_actualized_over_planned_percentage = (total_actualized_count / planned_count * 100.0) if planned_count else 0.0
    planned_share_of_actualized_percentage = (
        actualized_planned_count / total_actualized_count * 100.0
        if total_actualized_count
        else 0.0
    )
    return SummaryRow(
        branch=branch,
        planned_count=planned_count,
        actualized_planned_count=actualized_planned_count,
        total_actualized_count=total_actualized_count,
        unplanned_actualized_count=unplanned_actualized_count,
        planned_completion_percentage=planned_completion_percentage,
        total_actualized_over_planned_percentage=total_actualized_over_planned_percentage,
        planned_share_of_actualized_percentage=planned_share_of_actualized_percentage,
    )


def _filter_task_dependent(activities: list[Activity]) -> list[Activity]:
    return [activity for activity in activities if is_task_dependent_type(activity.activity_type)]


def _previous_horizon_date(activity: Activity, date_type: str) -> datetime | None:
    if date_type == "start":
        if activity.actual_start is not None:
            return None
        return activity.planned_start or activity.remaining_start

    if activity.actual_finish is not None:
        return None
    return activity.planned_finish or activity.remaining_finish


def _is_within_tracking_window(
    activity_date: datetime,
    previous_data_date: datetime,
    current_data_date: datetime,
) -> bool:
    return previous_data_date < activity_date <= current_data_date


def _project_match_key(schedule: XerSchedule) -> str:
    name = _normalize_project_base_name(schedule.project.name)
    if name:
        return name
    return normalize_text(schedule.project.project_id)


def _project_key_map(schedules: list[XerSchedule]) -> dict[str, XerSchedule]:
    mapping: dict[str, XerSchedule] = {}
    for schedule in schedules:
        key = _project_match_key(schedule)
        if key and key not in mapping:
            mapping[key] = schedule
    return mapping


def _normalize_project_base_name(value: str | None) -> str:
    stripped = _strip_project_schedule_suffix(value)
    normalized = normalize_text(stripped)
    if not normalized:
        return ""

    collapsed = re.sub(r"[\s._-]+", " ", normalized).strip()
    return collapsed or normalized


def _display_project_name(value: str | None) -> str:
    return _strip_project_schedule_suffix(value)


def _strip_project_schedule_suffix(value: str | None) -> str:
    raw_value = (value or "").strip()
    if not raw_value:
        return ""

    match = re.match(
        r"^(.*?)(?:[\s._-]+)?\d{4}[./-]\d{2}[./-]\d{2}(?:[\s._-]*\([^)]*\)|[\s._-]+[A-Za-z0-9]+)*\s*$",
        raw_value,
    )
    base_value = match.group(1) if match else raw_value
    display = re.sub(r"\s+", " ", base_value).strip(" ._-")
    return display or raw_value
