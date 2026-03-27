from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ppc_app.analyzer import analyze_schedule_collections, analyze_schedules
from ppc_app.xer_parser import parse_xer_file, parse_xer_projects


class AnalysisTests(unittest.TestCase):
    def test_multiple_projects_are_analyzed_separately(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            previous_file = temp_path / "previous.xer"
            current_file = temp_path / "current.xer"

            previous_file.write_text(
                "\n".join(
                    [
                        "ERMHDR\t9.0",
                        "%T\tPROJECT",
                        "%F\tproj_id\tproj_short_name\tlast_recalc_date",
                        "%R\t1\tProject-A 2024.01.31\t2024-01-31 08:00",
                        "%R\t2\tProject-B - 2024-01-31\t2024-01-31 08:00",
                        "%T\tPROJWBS",
                        "%F\twbs_id\tproj_id\tparent_wbs_id\twbs_short_name\twbs_name",
                        "%R\t10\t1\t999\tProject-A 2024.01.31\tProject Alpha Campus 2024.01.31",
                        "%R\t11\t1\t10\tCON\tConstruction",
                        "%R\t20\t2\t999\tProject-B - 2024-01-31\tProject Beta Lodge - 2024-01-31",
                        "%R\t21\t2\t20\tIPP\tIntegrated Phased Planning",
                        "%T\tTASK",
                        "%F\ttask_id\tproj_id\twbs_id\ttask_code\ttask_name\ttask_type\trestart_date\treend_date\tearly_start_date\tearly_end_date\ttarget_start_date\ttarget_end_date\tact_start_date\tact_end_date",
                        "%R\t100\t1\t11\tA-100\tProject A Task\tTask Dependent\t2024-02-02 08:00\t2024-02-05 17:00\t2024-02-02 08:00\t2024-02-05 17:00\t2024-02-02 08:00\t2024-02-05 17:00\t\t",
                        "%R\t200\t2\t21\tB-100\tProject B Task\tTask Dependent\t2024-02-03 08:00\t2024-02-06 17:00\t2024-02-03 08:00\t2024-02-06 17:00\t2024-02-03 08:00\t2024-02-06 17:00\t\t",
                    ]
                ),
                encoding="utf-8",
            )

            current_file.write_text(
                "\n".join(
                    [
                        "ERMHDR\t9.0",
                        "%T\tPROJECT",
                        "%F\tproj_id\tproj_short_name\tlast_recalc_date",
                        "%R\t1\tProject-A 2024.02.15 OG\t2024-02-15 08:00",
                        "%R\t2\tProject-B - 2024-02-15\t2024-02-15 08:00",
                        "%T\tPROJWBS",
                        "%F\twbs_id\tproj_id\tparent_wbs_id\twbs_short_name\twbs_name",
                        "%R\t10\t1\t999\tProject-A 2024.02.15 OG\tProject Alpha Campus 2024.02.15 OG",
                        "%R\t11\t1\t10\tCON\tConstruction",
                        "%R\t20\t2\t999\tProject-B - 2024-02-15\tProject Beta Lodge - 2024-02-15",
                        "%R\t21\t2\t20\tIPP\tIPP",
                        "%T\tTASK",
                        "%F\ttask_id\tproj_id\twbs_id\ttask_code\ttask_name\ttask_type\trestart_date\treend_date\tearly_start_date\tearly_end_date\ttarget_start_date\ttarget_end_date\tact_start_date\tact_end_date",
                        "%R\t100\t1\t11\tA-100\tProject A Task\tTask Dependent\t2024-02-02 08:00\t2024-02-05 17:00\t2024-02-02 08:00\t2024-02-05 17:00\t2024-02-02 08:00\t2024-02-05 17:00\t2024-02-02 08:00\t2024-02-05 17:00",
                        "%R\t200\t2\t21\tB-100\tProject B Task\tTask Dependent\t2024-02-03 08:00\t2024-02-06 17:00\t2024-02-03 08:00\t2024-02-06 17:00\t2024-02-03 08:00\t2024-02-06 17:00\t2024-02-03 08:00\t2024-02-06 17:00",
                    ]
                ),
                encoding="utf-8",
            )

            result = analyze_schedule_collections(parse_xer_projects(previous_file), parse_xer_projects(current_file))

            self.assertEqual(len(result.project_results), 2)
            project_names = [project.project_name for project in result.project_results]
            display_names = [project.display_name for project in result.project_results]
            self.assertEqual(project_names, ["Project Alpha Campus 2024.01.31", "Project Beta Lodge - 2024-01-31"])
            self.assertEqual(display_names, ["Project Alpha Campus", "Project Beta Lodge"])

    def test_project_matching_ignores_date_and_trailing_annotations(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            previous_file = temp_path / "previous.xer"
            current_file = temp_path / "current.xer"

            previous_file.write_text(
                "\n".join(
                    [
                        "ERMHDR\t9.0",
                        "%T\tPROJECT",
                        "%F\tproj_id\tproj_short_name\tlast_recalc_date",
                        "%R\t1\tUP-100\t2024-03-03 17:00",
                        "%T\tPROJWBS",
                        "%F\twbs_id\tproj_id\tparent_wbs_id\twbs_short_name\twbs_name",
                        "%R\t10\t1\t999\tUP-100\tFAcT - Future Aircrew Training - Moose Jaw - 2026.03.03 (WhatIf)- OG",
                        "%R\t11\t1\t10\tCON\tConstruction",
                        "%T\tTASK",
                        "%F\ttask_id\tproj_id\twbs_id\ttask_code\ttask_name\ttask_type\trestart_date\treend_date\tearly_start_date\tearly_end_date\ttarget_start_date\ttarget_end_date\tact_start_date\tact_end_date",
                        "%R\t100\t1\t11\tA-100\tProject Task\tTask Dependent\t2024-03-04 08:00\t2024-03-07 17:00\t2024-03-04 08:00\t2024-03-07 17:00\t2024-03-04 08:00\t2024-03-07 17:00\t\t",
                    ]
                ),
                encoding="utf-8",
            )

            current_file.write_text(
                "\n".join(
                    [
                        "ERMHDR\t9.0",
                        "%T\tPROJECT",
                        "%F\tproj_id\tproj_short_name\tlast_recalc_date",
                        "%R\t1\tOG-100\t2024-03-26 17:00",
                        "%T\tPROJWBS",
                        "%F\twbs_id\tproj_id\tparent_wbs_id\twbs_short_name\twbs_name",
                        "%R\t10\t1\t999\tOG-100\tFAcT - Future Aircrew Training - Moose Jaw - 2026.03.26 (WhatIf)",
                        "%R\t11\t1\t10\tCON\tConstruction",
                        "%T\tTASK",
                        "%F\ttask_id\tproj_id\twbs_id\ttask_code\ttask_name\ttask_type\trestart_date\treend_date\tearly_start_date\tearly_end_date\ttarget_start_date\ttarget_end_date\tact_start_date\tact_end_date",
                        "%R\t100\t1\t11\tA-100\tProject Task\tTask Dependent\t2024-03-04 08:00\t2024-03-07 17:00\t2024-03-04 08:00\t2024-03-07 17:00\t2024-03-04 08:00\t2024-03-07 17:00\t2024-03-04 08:00\t2024-03-07 17:00",
                    ]
                ),
                encoding="utf-8",
            )

            result = analyze_schedule_collections(parse_xer_projects(previous_file), parse_xer_projects(current_file))

            self.assertEqual(len(result.project_results), 1)
            self.assertEqual(result.project_results[0].display_name, "FAcT - Future Aircrew Training - Moose Jaw")

    def test_actuals_on_previous_data_date_are_excluded(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            previous_file = temp_path / "previous.xer"
            current_file = temp_path / "current.xer"

            previous_file.write_text(
                "\n".join(
                    [
                        "ERMHDR\t9.0",
                        "%T\tPROJECT",
                        "%F\tproj_id\tproj_short_name\tlast_recalc_date",
                        "%R\t1\tDemo\t2024-01-31 17:00",
                        "%T\tPROJWBS",
                        "%F\twbs_id\tproj_id\tparent_wbs_id\twbs_short_name\twbs_name",
                        "%R\t11\t1\t\tCON\tConstruction",
                        "%T\tTASK",
                        "%F\ttask_id\tproj_id\twbs_id\ttask_code\ttask_name\ttask_type\trestart_date\treend_date\tearly_start_date\tearly_end_date\ttarget_start_date\ttarget_end_date\tact_start_date\tact_end_date",
                        "%R\t100\t1\t11\tC100\tMain Work\tTask Dependent\t2024-02-01 08:00\t2024-02-05 17:00\t2024-02-01 08:00\t2024-02-05 17:00\t2024-02-01 08:00\t2024-02-05 17:00\t\t",
                    ]
                ),
                encoding="utf-8",
            )

            current_file.write_text(
                "\n".join(
                    [
                        "ERMHDR\t9.0",
                        "%T\tPROJECT",
                        "%F\tproj_id\tproj_short_name\tlast_recalc_date",
                        "%R\t1\tDemo\t2024-02-07 17:00",
                        "%T\tPROJWBS",
                        "%F\twbs_id\tproj_id\tparent_wbs_id\twbs_short_name\twbs_name",
                        "%R\t11\t1\t\tCON\tConstruction",
                        "%T\tTASK",
                        "%F\ttask_id\tproj_id\twbs_id\ttask_code\ttask_name\ttask_type\trestart_date\treend_date\tearly_start_date\tearly_end_date\ttarget_start_date\ttarget_end_date\tact_start_date\tact_end_date",
                        "%R\t100\t1\t11\tC100\tMain Work\tTask Dependent\t2024-02-01 08:00\t2024-02-05 17:00\t2024-02-01 08:00\t2024-02-05 17:00\t2024-02-01 08:00\t2024-02-05 17:00\t2024-02-01 08:00\t2024-01-31 17:00",
                    ]
                ),
                encoding="utf-8",
            )

            result = analyze_schedules(parse_xer_file(previous_file), parse_xer_file(current_file))
            finishes = {row.branch: row for row in result.finishes_summary}

            self.assertEqual(finishes["Construction"].planned_count, 1)
            self.assertEqual(finishes["Construction"].actualized_planned_count, 0)
            self.assertEqual(finishes["Construction"].total_actualized_count, 0)
            self.assertEqual(finishes["Construction"].unplanned_actualized_count, 0)

    def test_integrated_phased_planning_branch_is_tracked(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            previous_file = temp_path / "previous.xer"
            current_file = temp_path / "current.xer"

            previous_file.write_text(
                "\n".join(
                    [
                        "ERMHDR\t9.0",
                        "%T\tPROJECT",
                        "%F\tproj_id\tproj_short_name\tlast_recalc_date",
                        "%R\t1\tDemo\t2024-01-31 08:00",
                        "%T\tPROJWBS",
                        "%F\twbs_id\tproj_id\tparent_wbs_id\twbs_short_name\twbs_name",
                        "%R\t10\t1\t\tIPP\tIntegrated Phased Planning",
                        "%R\t11\t1\t10\tIPP-01\tIPP Area",
                        "%T\tTASK",
                        "%F\ttask_id\tproj_id\twbs_id\ttask_code\ttask_name\ttask_type\trestart_date\treend_date\tearly_start_date\tearly_end_date\ttarget_start_date\ttarget_end_date\tact_start_date\tact_end_date",
                        "%R\t100\t1\t11\tIPP-100\tIPP Coordination\tTask Dependent\t2024-02-02 08:00\t2024-02-05 17:00\t2024-02-02 08:00\t2024-02-05 17:00\t2024-02-02 08:00\t2024-02-05 17:00\t\t",
                    ]
                ),
                encoding="utf-8",
            )

            current_file.write_text(
                "\n".join(
                    [
                        "ERMHDR\t9.0",
                        "%T\tPROJECT",
                        "%F\tproj_id\tproj_short_name\tlast_recalc_date",
                        "%R\t1\tDemo\t2024-02-15 08:00",
                        "%T\tPROJWBS",
                        "%F\twbs_id\tproj_id\tparent_wbs_id\twbs_short_name\twbs_name",
                        "%R\t10\t1\t\tIPP\tIntegrated Phased Planning",
                        "%R\t11\t1\t10\tIPP-01\tIPP Area",
                        "%T\tTASK",
                        "%F\ttask_id\tproj_id\twbs_id\ttask_code\ttask_name\ttask_type\trestart_date\treend_date\tearly_start_date\tearly_end_date\ttarget_start_date\ttarget_end_date\tact_start_date\tact_end_date",
                        "%R\t100\t1\t11\tIPP-100\tIPP Coordination\tTask Dependent\t2024-02-02 08:00\t2024-02-05 17:00\t2024-02-02 08:00\t2024-02-05 17:00\t2024-02-02 08:00\t2024-02-05 17:00\t2024-02-02 08:00\t2024-02-05 17:00",
                    ]
                ),
                encoding="utf-8",
            )

            result = analyze_schedules(parse_xer_file(previous_file), parse_xer_file(current_file))
            starts = {row.branch: row for row in result.starts_summary}
            finishes = {row.branch: row for row in result.finishes_summary}

            self.assertEqual(starts["Integrated Phased Planning"].planned_count, 1)
            self.assertEqual(starts["Integrated Phased Planning"].actualized_planned_count, 1)
            self.assertEqual(finishes["Integrated Phased Planning"].planned_count, 1)
            self.assertEqual(finishes["Integrated Phased Planning"].actualized_planned_count, 1)

    def test_post_construction_is_excluded_from_construction_branch(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            previous_file = temp_path / "previous.xer"
            current_file = temp_path / "current.xer"

            file_text = "\n".join(
                [
                    "ERMHDR\t9.0",
                    "%T\tPROJECT",
                    "%F\tproj_id\tproj_short_name\tlast_recalc_date",
                    "%R\t1\tDemo\t2024-01-31 08:00",
                    "%T\tPROJWBS",
                    "%F\twbs_id\tproj_id\tparent_wbs_id\twbs_short_name\twbs_name",
                    "%R\t11\t1\t\tCON\tConstruction Phase",
                    "%R\t12\t1\t\tPOST\tPost Construction",
                    "%T\tTASK",
                    "%F\ttask_id\tproj_id\twbs_id\ttask_code\ttask_name\ttask_type\trestart_date\treend_date\tearly_start_date\tearly_end_date\ttarget_start_date\ttarget_end_date\tact_start_date\tact_end_date",
                    "%R\t100\t1\t11\tC100\tMain Work\tTask Dependent\t2024-02-02 08:00\t2024-02-07 17:00\t2024-02-02 08:00\t2024-02-07 17:00\t2024-02-02 08:00\t2024-02-07 17:00\t\t",
                    "%R\t101\t1\t12\tP100\tCloseout\tTask Dependent\t2024-02-03 08:00\t2024-02-08 17:00\t2024-02-03 08:00\t2024-02-08 17:00\t2024-02-03 08:00\t2024-02-08 17:00\t\t",
                ]
            )

            previous_file.write_text(file_text, encoding="utf-8")
            current_file.write_text(file_text.replace("2024-01-31 08:00", "2024-02-15 08:00", 1), encoding="utf-8")

            previous_schedule = parse_xer_file(previous_file)
            current_schedule = parse_xer_file(current_file)

            result = analyze_schedules(previous_schedule, current_schedule)
            starts = {row.branch: row for row in result.starts_summary}

            self.assertEqual(starts["Construction"].planned_count, 1)
            self.assertEqual(result.start_details[0].activity_id, "C100")

    def test_highest_relevant_wbs_branch_wins_over_leaf_name(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            previous_file = temp_path / "previous.xer"
            current_file = temp_path / "current.xer"

            file_text = "\n".join(
                [
                    "ERMHDR\t9.0",
                    "%T\tPROJECT",
                    "%F\tproj_id\tproj_short_name\tlast_recalc_date",
                    "%R\t1\tDemo\t2024-01-31 08:00",
                    "%T\tPROJWBS",
                    "%F\twbs_id\tproj_id\tparent_wbs_id\twbs_short_name\twbs_name",
                    "%R\t10\t1\t\tPRECON\tPreconstruction",
                    "%R\t11\t1\t10\tSUPPORT\tConstruction Support",
                    "%R\t12\t1\t\tCON\tConstruction",
                    "%T\tTASK",
                    "%F\ttask_id\tproj_id\twbs_id\ttask_code\ttask_name\ttask_type\trestart_date\treend_date\tearly_start_date\tearly_end_date\ttarget_start_date\ttarget_end_date\tact_start_date\tact_end_date",
                    "%R\t100\t1\t11\tP100\tPrecon Scoped Task\tTask Dependent\t2024-02-02 08:00\t2024-02-07 17:00\t2024-02-02 08:00\t2024-02-07 17:00\t2024-02-02 08:00\t2024-02-07 17:00\t\t",
                    "%R\t101\t1\t12\tC100\tConstruction Task\tTask Dependent\t2024-02-03 08:00\t2024-02-08 17:00\t2024-02-03 08:00\t2024-02-08 17:00\t2024-02-03 08:00\t2024-02-08 17:00\t\t",
                ]
            )

            previous_file.write_text(file_text, encoding="utf-8")
            current_file.write_text(file_text.replace("2024-01-31 08:00", "2024-02-15 08:00", 1), encoding="utf-8")

            previous_schedule = parse_xer_file(previous_file)

            preconstruction_ids = {activity.activity_id for activity in previous_schedule.activities_in_branch("Preconstruction")}
            construction_ids = {activity.activity_id for activity in previous_schedule.activities_in_branch("Construction")}

            self.assertEqual(preconstruction_ids, {"P100"})
            self.assertEqual(construction_ids, {"C100"})

    def test_analysis_matches_by_activity_id_and_name(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            previous_file = temp_path / "previous.xer"
            current_file = temp_path / "current.xer"

            previous_file.write_text(
                "\n".join(
                    [
                        "ERMHDR\t9.0",
                        "%T\tPROJECT",
                        "%F\tproj_id\tproj_short_name\tlast_recalc_date",
                        "%R\t1\tDemo\t2024-01-31 08:00",
                        "%T\tPROJWBS",
                        "%F\twbs_id\tproj_id\tparent_wbs_id\twbs_short_name\twbs_name",
                        "%R\t10\t1\t\tPRECON\tPre-Construction",
                        "%R\t11\t1\t\tCON\tConstruction",
                        "%R\t12\t1\t10\tPRE-01\tPreconstruction Area",
                        "%R\t13\t1\t11\tCON-01\tConstruction Area",
                        "%T\tTASK",
                        "%F\ttask_id\tproj_id\twbs_id\ttask_code\ttask_name\ttask_type\trestart_date\treend_date\tearly_start_date\tearly_end_date\ttarget_start_date\ttarget_end_date\tact_start_date\tact_end_date",
                        "%R\t100\t1\t12\tA100\tEarly Permit\tTask Dependent\t2024-02-02 08:00\t2024-02-07 17:00\t2024-02-02 08:00\t2024-02-07 17:00\t2024-02-02 08:00\t2024-02-07 17:00\t\t",
                        "%R\t101\t1\t12\tA101\tLong Lead Review\tTask Dependent\t2024-02-03 08:00\t2024-02-08 17:00\t2024-02-03 08:00\t2024-02-08 17:00\t2024-02-03 08:00\t2024-02-08 17:00\t\t",
                        "%R\t200\t1\t13\tB200\tSite Prep\tTask Dependent\t2024-02-04 08:00\t2024-02-09 17:00\t2024-02-04 08:00\t2024-02-09 17:00\t2024-02-04 08:00\t2024-02-09 17:00\t\t",
                        "%R\t201\t1\t13\tB201\tConcrete\tTask Dependent\t2024-02-05 08:00\t2024-02-10 17:00\t2024-02-05 08:00\t2024-02-10 17:00\t2024-02-05 08:00\t2024-02-10 17:00\t\t",
                        "%R\t202\t1\t13\tB202\tLate Procurement\tTask Dependent\t2024-03-05 08:00\t2024-03-12 17:00\t2024-03-05 08:00\t2024-03-12 17:00\t2024-03-05 08:00\t2024-03-12 17:00\t\t",
                        "%R\t203\t1\t13\tB203\tOwner Approval Milestone\tFinish Milestone\t2024-02-06 08:00\t2024-02-06 08:00\t2024-02-06 08:00\t2024-02-06 08:00\t2024-02-06 08:00\t2024-02-06 08:00\t\t",
                        "%R\t204\t1\t13\tB204\tFraming Closeout\tTask Dependent\t2024-01-31 08:00\t2024-02-12 17:00\t2024-01-20 08:00\t2024-02-12 17:00\t2024-01-20 08:00\t2024-03-01 17:00\t2024-01-25 08:00\t",
                    ]
                ),
                encoding="utf-8",
            )

            current_file.write_text(
                "\n".join(
                    [
                        "ERMHDR\t9.0",
                        "%T\tPROJECT",
                        "%F\tproj_id\tproj_short_name\tlast_recalc_date",
                        "%R\t1\tDemo\t2024-02-15 08:00",
                        "%T\tPROJWBS",
                        "%F\twbs_id\tproj_id\tparent_wbs_id\twbs_short_name\twbs_name",
                        "%R\t10\t1\t\tPRECON\tPre-Construction",
                        "%R\t11\t1\t\tCON\tConstruction",
                        "%R\t12\t1\t10\tPRE-01\tPreconstruction Area",
                        "%R\t13\t1\t11\tCON-01\tConstruction Area",
                        "%T\tTASK",
                        "%F\ttask_id\tproj_id\twbs_id\ttask_code\ttask_name\ttask_type\trestart_date\treend_date\tearly_start_date\tearly_end_date\ttarget_start_date\ttarget_end_date\tact_start_date\tact_end_date",
                        "%R\t100\t1\t12\tA100\tEarly Permit\tTask Dependent\t2024-02-02 08:00\t2024-02-07 17:00\t2024-02-02 08:00\t2024-02-07 17:00\t2024-02-02 08:00\t2024-02-07 17:00\t2024-02-02 08:00\t2024-02-07 17:00",
                        "%R\t101\t1\t12\t\tLong Lead Review\tTask Dependent\t2024-02-03 08:00\t2024-02-08 17:00\t2024-02-03 08:00\t2024-02-08 17:00\t2024-02-03 08:00\t2024-02-08 17:00\t2024-02-03 08:00\t",
                        "%R\t200\t1\t13\tB200\tSite Prep\tTask Dependent\t2024-02-04 08:00\t2024-02-09 17:00\t2024-02-04 08:00\t2024-02-09 17:00\t2024-02-04 08:00\t2024-02-09 17:00\t2024-02-04 08:00\t2024-02-09 17:00",
                        "%R\t201\t1\t13\tB201\tConcrete\tTask Dependent\t2024-02-05 08:00\t2024-02-10 17:00\t2024-02-05 08:00\t2024-02-10 17:00\t2024-02-05 08:00\t2024-02-10 17:00\t\t",
                        "%R\t202\t1\t13\tB202\tLate Procurement\tTask Dependent\t2024-03-05 08:00\t2024-03-12 17:00\t2024-03-05 08:00\t2024-03-12 17:00\t2024-03-05 08:00\t2024-03-12 17:00\t2024-02-06 08:00\t2024-02-11 17:00",
                        "%R\t203\t1\t13\tB203\tOwner Approval Milestone\tFinish Milestone\t2024-02-06 08:00\t2024-02-06 08:00\t2024-02-06 08:00\t2024-02-06 08:00\t2024-02-06 08:00\t2024-02-06 08:00\t2024-02-06 08:00\t2024-02-06 08:00",
                        "%R\t204\t1\t13\tB204\tFraming Closeout\tTask Dependent\t2024-02-15 08:00\t2024-02-12 17:00\t2024-01-20 08:00\t2024-02-12 17:00\t2024-01-20 08:00\t2024-03-01 17:00\t2024-01-25 08:00\t2024-02-12 17:00",
                    ]
                ),
                encoding="utf-8",
            )

            previous_schedule = parse_xer_file(previous_file)
            current_schedule = parse_xer_file(current_file)

            result = analyze_schedules(previous_schedule, current_schedule)

            starts = {row.branch: row for row in result.starts_summary}
            finishes = {row.branch: row for row in result.finishes_summary}

            self.assertEqual(starts["Preconstruction"].planned_count, 2)
            self.assertEqual(starts["Preconstruction"].actualized_planned_count, 2)
            self.assertEqual(starts["Preconstruction"].total_actualized_count, 2)
            self.assertEqual(starts["Preconstruction"].unplanned_actualized_count, 0)
            self.assertEqual(finishes["Preconstruction"].planned_count, 2)
            self.assertEqual(finishes["Preconstruction"].actualized_planned_count, 1)
            self.assertEqual(finishes["Preconstruction"].total_actualized_count, 1)
            self.assertEqual(finishes["Preconstruction"].unplanned_actualized_count, 0)

            self.assertEqual(starts["Construction"].planned_count, 2)
            self.assertEqual(starts["Construction"].actualized_planned_count, 1)
            self.assertEqual(starts["Construction"].total_actualized_count, 2)
            self.assertEqual(starts["Construction"].unplanned_actualized_count, 1)
            self.assertEqual(finishes["Construction"].planned_count, 3)
            self.assertEqual(finishes["Construction"].actualized_planned_count, 2)
            self.assertEqual(finishes["Construction"].total_actualized_count, 3)
            self.assertEqual(finishes["Construction"].unplanned_actualized_count, 1)

            self.assertAlmostEqual(starts["Construction"].planned_completion_percentage, 50.0)
            self.assertAlmostEqual(starts["Construction"].planned_share_of_actualized_percentage, 50.0)
            self.assertAlmostEqual(finishes["Construction"].planned_completion_percentage, 66.6666666667, places=1)
            self.assertAlmostEqual(finishes["Construction"].planned_share_of_actualized_percentage, 66.6666666667, places=1)

            self.assertEqual(len(result.actualized_planned_start_details), 3)
            self.assertEqual(len(result.actualized_unplanned_start_details), 1)
            self.assertEqual(len(result.actualized_planned_finish_details), 3)
            self.assertEqual(len(result.actualized_unplanned_finish_details), 1)

            unplanned_start = result.actualized_unplanned_start_details[0]
            self.assertEqual(unplanned_start.activity_name, "Late Procurement")
            planned_finish_names = {detail.activity_name for detail in result.actualized_planned_finish_details}
            self.assertIn("Framing Closeout", planned_finish_names)
            self.assertNotIn(
                "Owner Approval Milestone",
                {detail.activity_name for detail in result.actualized_unplanned_start_details},
            )
            self.assertNotIn(
                "Owner Approval Milestone",
                {detail.activity_name for detail in result.actualized_unplanned_finish_details},
            )

            precon_name_match = next(
                detail for detail in result.start_details if detail.activity_name == "Long Lead Review"
            )
            self.assertEqual(precon_name_match.match_method, "Activity Name")


if __name__ == "__main__":
    unittest.main()
